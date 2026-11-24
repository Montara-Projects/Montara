#!/usr/bin/env python3
"""Operator-only E2E: upload real workspace to R2 EU, verify, restore and open.

No deletion and no production route modifications. Exit nonzero unless *all*
gates pass. Credentials come only from an already-authorized secure runtime.
Never pass tokens as command-line arguments or commit them to GitHub.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

from urano.r2_workspace_archive import (
    Boto3R2Store, R2SnapshotError,
    prepare_editor_scratch, restore_workspace,
    snapshot_workspace, verify_snapshot,
)
from urano.r2_tenant_routing import verified_tenant_for_owner


def _trusted_owner_registry(path: Path) -> dict[str, str]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise R2SnapshotError("Private trusted owner registry required")
    s = path.stat()
    if not stat.S_ISREG(s.st_mode) or s.st_mode & 0o077:
        raise R2SnapshotError("Owner registry permissions too broad")
    data = json.loads(path.read_text(encoding="utf8"))
    if (not isinstance(data, dict) or
            any(type(k) is not str or type(v) is not str
                for k, v in data.items())):
        raise R2SnapshotError("Invalid owner registry")
    return data


def _run(args) -> dict:
    registry = _trusted_owner_registry(args.owner_registry)
    expected_tenant = verified_tenant_for_owner(
        trusted_instance=args.trusted_instance,
        verified_owner_id=args.verified_owner_id,
        owner_tenants=registry,
    )
    root = args.source_root
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise R2SnapshotError("Source must be an existing absolute private workspace")
    dest = args.restore_to
    if not dest.is_absolute() or dest.exists() or dest.is_symlink():
        raise R2SnapshotError("New absolute restore destination required")
    if dest.is_relative_to(root) or root.is_relative_to(dest):
        raise R2SnapshotError("R2 restore destination must be independent")
    key_id = os.environ.get("MONTARA_STORAGE_EU_V2_KEY_ID")
    secret = os.environ.get("MONTARA_STORAGE_EU_V2_SECRET")
    if not key_id or not secret:
        raise R2SnapshotError("EU R2 credentials unavailable in secure runtime")
    store = Boto3R2Store.from_credentials(
        access_key_id=key_id, secret_access_key=secret)
    # Every uploaded and downloaded object is hashed, never trust S3 ETags.
    saved = snapshot_workspace(
        root=root, store=store, trusted_instance=args.trusted_instance,
        verified_owner_id=args.verified_owner_id, owner_tenants=registry)
    checked = verify_snapshot(
        store=store, tenant=saved.tenant, snapshot_id=saved.snapshot_id)
    if saved != checked:
        raise R2SnapshotError("S3 verified snapshot receipt mismatch")
    restored = restore_workspace(
        store=store, tenant=saved.tenant, snapshot_id=saved.snapshot_id,
        destination=dest, expected_manifest_sha256=saved.sha256)
    if restored != checked:
        raise R2SnapshotError("Restored snapshot differs from remote verification")
    adjusted = prepare_editor_scratch(
        store=store, tenant=saved.tenant, snapshot_id=saved.snapshot_id,
        expected_manifest_sha256=saved.sha256, restored_root=dest)
    # Require the actual native engine loader, not only JSON parsing.
    from core.project import load_project
    recovered = sorted((dest / "Projects").glob("*.zuckervid/project.json"))
    if not recovered:
        raise R2SnapshotError("No native projects available after restore")
    validated = 0
    for project_json in recovered:
        project = load_project(str(project_json.parent), ensure_dirs=False)
        inputs = project.data.get("inputs", {})
        all_inputs = [
            *(inputs.get("videos") or []),
            *[x for x in (inputs.get("master"), inputs.get("songs")) if x],
        ]
        for entry in all_inputs:
            media_path = Path(entry["path"])
            if (not media_path.is_relative_to(dest) or
                    not media_path.is_file()):
                raise R2SnapshotError("Editor still depends on a VM original")
        validated += 1
    return {
        "result": "PASS_FULL_R2_EU_ROUNDTRIP",
        "tenant": expected_tenant,
        "snapshot_id": saved.snapshot_id,
        "manifest_key": saved.manifest_key,
        "manifest_sha256": saved.sha256,
        "files_sha256_verified": checked.files,
        "bytes_sha256_verified": checked.bytes,
        "native_projects_opened": validated,
        "runtime_project_paths_rebound": adjusted,
        "source_originals_removed": False,
        "restore_root": str(dest),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trusted-instance", required=True)
    ap.add_argument("--verified-owner-id", required=True)
    ap.add_argument("--owner-registry", type=Path, required=True)
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--restore-to", type=Path, required=True)
    ap.add_argument("--proof-json", type=Path, required=True,
                    help="Private new path for the verification receipt")
    args = ap.parse_args()
    if (not args.proof_json.is_absolute() or args.proof_json.is_symlink()
            or args.proof_json.exists()):
        print("BLOCKED: proof output must be a new absolute path", file=sys.stderr)
        return 2
    try:
        result = _run(args)
        fd = os.open(args.proof_json, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf8") as out:
            json.dump(result, out, indent=2)
            out.write("\n")
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        # Avoid echoing S3 error bodies containing account or credential info.
        print("ROUNDTRIP_NOT_VERIFIED:", type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
