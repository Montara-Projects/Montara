"""Verified, immutable R2 EU workspace snapshots and safe materialization.

This is the isolated project-migration/restore building block, NOT a live
request route. The live gateway must first authorize OAuth owner+project,
reserve tenant quota, and supply a private authenticated R2 object store.

Migration's proof order is:
  local source -> R2 objects -> GET each R2 object and independently SHA-256
  -> commit R2 manifest -> restore to a separate scratch workspace
  -> open native project -> only then consider explicit source removal.

Never treat multipart S3 ETag or metadata alone as a full-file checksum.
No source deletion is performed by this module.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import stat
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Protocol
from uuid import UUID, uuid4

from urano.r2_tenant_routing import (
    R2_BUCKET, R2_ENDPOINT, TenantRoutingDenied,
    verified_tenant_for_owner,
)

CHUNK = 4 * 1024 * 1024
MANIFEST_LIMIT = 32 * 1024 * 1024
_ALLOWED_ROOTS = frozenset({
    "Projects", "Sessions", "Uploads", "WizardUploads",
    "Mixer", "Branding", "Inbox", "PushPacks", "config.json",
})
_TENANT = re.compile(r"pilot-(?:amehc|fergardel|t4t)\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class R2SnapshotError(RuntimeError):
    """Failed verification; do not change source or activate cloud cutover."""


class R2ObjectStore(Protocol):
    """Private object-store interface. Never supplied from a browser."""
    def put_file(self, key: str, source: Path, *, sha256: str) -> None: ...
    def put_bytes(self, key: str, body: bytes) -> None: ...
    def open(self, key: str) -> BinaryIO: ...


@dataclass(frozen=True)
class SnapshotReceipt:
    tenant: str
    snapshot_id: str
    manifest_key: str
    files: int
    bytes: int
    sha256: str


def _uuid(value: str) -> str:
    if type(value) is not str:
        raise R2SnapshotError("Expected canonical snapshot UUID")
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise R2SnapshotError("Invalid snapshot UUID") from exc
    if str(parsed) != value:
        raise R2SnapshotError("Non-canonical snapshot UUID")
    return value


def _tenant(tenant: str) -> str:
    if type(tenant) is not str or not _TENANT.fullmatch(tenant):
        raise R2SnapshotError("Unknown R2 tenant")
    return tenant


def _prefix(tenant: str, snapshot_id: str) -> str:
    return f"tenants/{_tenant(tenant)}/snapshots/{_uuid(snapshot_id)}"


def _relative_path(value: str) -> PurePosixPath:
    if type(value) is not str or not value or "\x00" in value or "\\" in value:
        raise R2SnapshotError("Invalid snapshot path")
    p = PurePosixPath(value)
    if (p.is_absolute() or any(part in ("", ".", "..") for part in value.split("/"))
            or len(p.parts) < 1 or p.parts[0] not in _ALLOWED_ROOTS):
        raise R2SnapshotError("Snapshot path escapes persistent workspace")
    if p.parts[0] == "config.json" and len(p.parts) != 1:
        raise R2SnapshotError("Invalid config location")
    return p


def _digest(source: BinaryIO) -> tuple[int, str]:
    sha = hashlib.sha256()
    size = 0
    while True:
        part = source.read(CHUNK)
        if not part:
            break
        sha.update(part)
        size += len(part)
    return size, sha.hexdigest()


def _read_limited(source: BinaryIO) -> bytes:
    data = source.read(MANIFEST_LIMIT + 1)
    if len(data) > MANIFEST_LIMIT:
        raise R2SnapshotError("Manifest size limit")
    return data


def _read_remote(store: R2ObjectStore, key: str) -> tuple[int, str]:
    stream = store.open(key)
    try:
        return _digest(stream)
    finally:
        stream.close()


def _stat_regular(root: Path, file: Path) -> os.stat_result:
    if file.is_symlink() or not file.is_file():
        raise R2SnapshotError("Unsupported linked or nonregular workspace file")
    # The controlled root cannot be redirected by symlinks in any parent.
    current = file.parent
    while current != root:
        if current.is_symlink():
            raise R2SnapshotError("Linked workspace parent")
        if not current.is_relative_to(root):
            raise R2SnapshotError("Workspace file outside root")
        current = current.parent
    info = file.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise R2SnapshotError("Nonregular workspace file")
    return info


def _source_files(root: Path):
    if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077:
        raise R2SnapshotError("Source workspace must be private")
    for first in sorted(_ALLOWED_ROOTS):
        path = root / first
        if not path.exists() and not path.is_symlink():
            continue
        if path.is_symlink():
            raise R2SnapshotError("Linked workspace scope")
        if first == "config.json":
            yield path
        elif path.is_dir():
            for folder, dirs, files in os.walk(path, topdown=True, followlinks=False):
                current = Path(folder)
                for name in dirs:
                    if (current / name).is_symlink():
                        raise R2SnapshotError("Linked workspace directory")
                for name in sorted(files):
                    yield current / name
        else:
            raise R2SnapshotError("Unexpected workspace scope type")


def _safe_record(record: dict, prefix: str) -> tuple[PurePosixPath, str, int, int, str]:
    if not isinstance(record, dict) or set(record) != {
        "path", "key", "bytes", "sha256", "mtime_ns",
    }:
        raise R2SnapshotError("Invalid snapshot record")
    rel = _relative_path(record["path"])
    key = f"{prefix}/files/{rel.as_posix()}"
    if record["key"] != key:
        raise R2SnapshotError("Object key doesn't match tenant snapshot")
    size, mtime, digest = record["bytes"], record["mtime_ns"], record["sha256"]
    if (type(size) is not int or size < 0 or
            type(mtime) is not int or mtime < 0 or
            type(digest) is not str or not _SHA.fullmatch(digest)):
        raise R2SnapshotError("Invalid snapshot hash or size")
    return rel, key, size, mtime, digest


def _manifest_key(tenant: str, snapshot_id: str) -> str:
    return f"{_prefix(tenant, snapshot_id)}/manifest.json"


def snapshot_workspace(*, root: Path, store: R2ObjectStore,
                       trusted_instance: str, verified_owner_id: str,
                       owner_tenants: dict[str, str],
                       snapshot_id: str | None = None) -> SnapshotReceipt:
    """Store and independently read-verify ALL selected persistent workspace files.

    The manifest is written LAST as an immutable commit marker. Reusing a
    snapshot UUID is prohibited by the calling broker; use fresh UUIDs.
    """
    try:
        tenant = verified_tenant_for_owner(
            trusted_instance=trusted_instance,
            verified_owner_id=verified_owner_id,
            owner_tenants=owner_tenants,
        )
    except TenantRoutingDenied as exc:
        raise R2SnapshotError("Tenant authorization failed") from exc
    sid = _uuid(snapshot_id) if snapshot_id else str(uuid4())
    prefix = _prefix(tenant, sid)
    base = Path(root)
    if not base.is_absolute() or base.is_symlink():
        raise R2SnapshotError("Absolute unlinked private source root required")
    base = base.resolve(strict=True)
    files = []
    total = 0
    for source in _source_files(base):
        rel = source.relative_to(base)
        key = f"{prefix}/files/{rel.as_posix()}"
        _relative_path(rel.as_posix())
        before = _stat_regular(base, source)
        with source.open("rb") as f:
            size, digest = _digest(f)
        if size != before.st_size:
            raise R2SnapshotError("Source changed before upload")
        store.put_file(key, source, sha256=digest)
        after = _stat_regular(base, source)
        if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
            raise R2SnapshotError("Source changed during upload")
        rsize, rhash = _read_remote(store, key)
        if (rsize, rhash) != (size, digest):
            raise R2SnapshotError("R2 readback hash mismatch")
        files.append({
            "path": rel.as_posix(), "key": key, "bytes": size,
            "sha256": digest, "mtime_ns": before.st_mtime_ns,
        })
        total += size
    if not any(f["path"].startswith("Projects/") and
               f["path"].endswith("/project.json") for f in files):
        raise R2SnapshotError("No saved native project; snapshot not committed")
    # Recheck *all* source files after the last multipart upload: a session
    # modified while another media object was uploading is not a consistent
    # workspace snapshot. Never publish its manifest.
    for record in files:
        path = base.joinpath(*_relative_path(record["path"]).parts)
        info = _stat_regular(base, path)
        if ((info.st_size, info.st_mtime_ns) !=
                (record["bytes"], record["mtime_ns"])):
            raise R2SnapshotError("Source changed before manifest commit")
        with path.open("rb") as stream:
            if _digest(stream) != (record["bytes"], record["sha256"]):
                raise R2SnapshotError("Source hash changed before commit")
    manifest = {
        "schema": 1, "tenant": tenant, "snapshot_id": sid,
        "bucket": R2_BUCKET, "jurisdiction": "eu",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(base), "files": files,
    }
    body = json.dumps(manifest, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")
    if len(body) > MANIFEST_LIMIT:
        raise R2SnapshotError("Snapshot manifest too large")
    key = _manifest_key(tenant, sid)
    store.put_bytes(key, body)
    readback = store.open(key)
    try:
        if _read_limited(readback) != body:
            raise R2SnapshotError("Manifest readback mismatch")
    finally:
        readback.close()
    return SnapshotReceipt(tenant, sid, key, len(files), total,
                           hashlib.sha256(body).hexdigest())


def _fetch_manifest(store: R2ObjectStore, tenant: str, snapshot_id: str) -> dict:
    key = _manifest_key(tenant, snapshot_id)
    stream = store.open(key)
    try:
        raw = _read_limited(stream)
    finally:
        stream.close()
    try:
        manifest = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise R2SnapshotError("Unparseable R2 manifest") from exc
    if (not isinstance(manifest, dict) or manifest.get("schema") != 1 or
            manifest.get("tenant") != tenant or
            manifest.get("snapshot_id") != snapshot_id or
            manifest.get("bucket") != R2_BUCKET or
            manifest.get("jurisdiction") != "eu" or
            not isinstance(manifest.get("files"), list) or
            not manifest["files"]):
        raise R2SnapshotError("Manifest identity, bucket or schema mismatch")
    prefix = _prefix(tenant, snapshot_id)
    seen = set()
    for record in manifest["files"]:
        rel, _, _, _, _ = _safe_record(record, prefix)
        if rel in seen:
            raise R2SnapshotError("Duplicate snapshot file")
        seen.add(rel)
    if not any(str(x).startswith("Projects/") and
               str(x).endswith("/project.json") for x in seen):
        raise R2SnapshotError("Manifest missing native project")
    return manifest


def verify_snapshot(*, store: R2ObjectStore, tenant: str,
                    snapshot_id: str) -> SnapshotReceipt:
    """Independently stream every R2 object, never trust ETag or metadata."""
    manifest = _fetch_manifest(store, _tenant(tenant), _uuid(snapshot_id))
    total = 0
    for record in manifest["files"]:
        _, key, size, _, digest = _safe_record(
            record, _prefix(tenant, snapshot_id))
        if _read_remote(store, key) != (size, digest):
            raise R2SnapshotError("R2 object digest differs from original")
        total += size
    key = _manifest_key(tenant, snapshot_id)
    raw = store.open(key)
    try:
        body = _read_limited(raw)
    finally:
        raw.close()
    return SnapshotReceipt(tenant, snapshot_id, key, len(manifest["files"]),
                           total, hashlib.sha256(body).hexdigest())


def restore_workspace(*, store: R2ObjectStore, tenant: str, snapshot_id: str,
                      destination: Path, expected_manifest_sha256: str
                      ) -> SnapshotReceipt:
    """Materialize one verified R2 snapshot to NEW isolated scratch.

    Never overwrite an existing workspace or delete an original. Call native
    editor's existing load_project() on the staged Projects tree to prove
    functional restore before activating this scratch directory.
    """
    tenant, snapshot_id = _tenant(tenant), _uuid(snapshot_id)
    if (type(expected_manifest_sha256) is not str or
            not _SHA.fullmatch(expected_manifest_sha256)):
        raise R2SnapshotError("Trusted manifest digest required")
    manifest_stream = store.open(_manifest_key(tenant, snapshot_id))
    try:
        manifest_body = _read_limited(manifest_stream)
    finally:
        manifest_stream.close()
    if hashlib.sha256(manifest_body).hexdigest() != expected_manifest_sha256:
        raise R2SnapshotError("R2 manifest has changed since trusted receipt")
    manifest = _fetch_manifest(store, tenant, snapshot_id)
    target = Path(destination)
    if not target.is_absolute() or target.exists() or target.is_symlink():
        raise R2SnapshotError("Destination must be a new absolute workspace")
    parent = target.parent
    if parent.is_symlink() or not parent.is_dir():
        raise R2SnapshotError("Untrusted restore parent")
    stage = Path(tempfile.mkdtemp(prefix=".r2-restore-", dir=parent))
    count = 0
    total = 0
    try:
        for record in manifest["files"]:
            rel, key, size, mtime, digest = _safe_record(
                record, _prefix(tenant, snapshot_id))
            out = stage.joinpath(*rel.parts)
            out.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if out.exists() or out.is_symlink():
                raise R2SnapshotError("Restored duplicate path")
            source = store.open(key)
            try:
                h = hashlib.sha256()
                received = 0
                with out.open("xb") as destination_file:
                    os.chmod(out, 0o600)
                    while chunk := source.read(CHUNK):
                        destination_file.write(chunk)
                        h.update(chunk)
                        received += len(chunk)
                    destination_file.flush()
                    os.fsync(destination_file.fileno())
            finally:
                source.close()
            if (received, h.hexdigest()) != (size, digest):
                raise R2SnapshotError("Restored R2 bytes differ from originals")
            os.utime(out, ns=(mtime, mtime))
            count += 1
            total += received
        if target.exists():
            raise R2SnapshotError("Restore destination appeared during download")
        stage.rename(target)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    raw = store.open(_manifest_key(tenant, snapshot_id))
    try:
        body = _read_limited(raw)
    finally:
        raw.close()
    return SnapshotReceipt(tenant, snapshot_id, _manifest_key(tenant, snapshot_id),
                           count, total, hashlib.sha256(body).hexdigest())


def prepare_editor_scratch(*, store: R2ObjectStore, tenant: str,
                           snapshot_id: str, expected_manifest_sha256: str,
                           restored_root: Path) -> int:
    """Rebind *throwaway local scratch* project paths after verified R2 restore.

    The immutable R2 copies never change. Montara's current native project
    schema stores absolute media paths, so a read-through materialization at
    another data_root needs its own runtime-only path mapping.

    All original-root file references must point inside this snapshot.
    Missing dependencies abort; never fall back to VM originals.
    """
    _tenant(tenant)
    _uuid(snapshot_id)
    manifest_stream = store.open(_manifest_key(tenant, snapshot_id))
    try:
        raw = _read_limited(manifest_stream)
    finally:
        manifest_stream.close()
    if hashlib.sha256(raw).hexdigest() != expected_manifest_sha256:
        raise R2SnapshotError("Untrusted snapshot identity")
    manifest = _fetch_manifest(store, tenant, snapshot_id)
    source_root = manifest.get("source_root")
    if type(source_root) is not str or not Path(source_root).is_absolute():
        raise R2SnapshotError("Snapshot source root unavailable")
    src_root = Path(source_root)
    dest = Path(restored_root)
    if dest.is_symlink() or not dest.is_dir():
        raise R2SnapshotError("Restored scratch workspace unavailable")
    dest = dest.resolve(strict=True)
    # Guard no implicit partial restore; all manifest files must exist in
    # restored root before editing even one runtime JSON.
    for record in manifest["files"]:
        rel, _, size, _, digest = _safe_record(
            record, _prefix(tenant, snapshot_id))
        candidate = dest.joinpath(*rel.parts)
        if candidate.is_symlink() or not candidate.is_file():
            raise R2SnapshotError("Missing restored project dependency")
        with candidate.open("rb") as stream:
            if _digest(stream) != (size, digest):
                raise R2SnapshotError("Restored project changed before rebind")
    patches = {}
    def repath(value):
        if isinstance(value, str) and value.startswith(str(src_root) + "/"):
            old = Path(value)
            try:
                relative = old.relative_to(src_root)
            except ValueError as exc:
                raise R2SnapshotError("Project source path outside workspace") from exc
            mapped = dest / relative
            if not mapped.exists() or mapped.is_symlink():
                raise R2SnapshotError("Native project depends on absent source")
            return str(mapped)
        if isinstance(value, list):
            return [repath(x) for x in value]
        if isinstance(value, dict):
            return {k: repath(x) for k, x in value.items()}
        return value
    # Plan every JSON rewrite first. Do not partially modify scratch if one
    # project contains a missing external dependency.
    for record in manifest["files"]:
        rel = _relative_path(record["path"])
        if (rel.parts[0] != "Projects" or len(rel.parts) < 3
                or rel.name not in {"project.json", "manifest.json",
                                    "native_recipe.json", "native_master.json"}):
            continue
        doc = dest.joinpath(*rel.parts)
        try:
            value = json.loads(doc.read_text(encoding="utf8"))
        except (UnicodeError, ValueError) as exc:
            raise R2SnapshotError("Unparseable restored project state") from exc
        mapped = repath(value)
        if mapped != value:
            patches[doc] = (json.dumps(mapped, ensure_ascii=False,
                                      indent=2) + "\n").encode("utf8")
    for path, body in patches.items():
        fd, name = tempfile.mkstemp(prefix=".r2-rebound-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(name, 0o600)
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
    return len(patches)


class Boto3R2Store:
    """Production-compatible S3 adapter, injected only by trusted backends.

    Install boto3 separately and provide temporary/scoped credentials from a
    secrets provider; do not put permanent R2 credentials in source or logs.
    """

    def __init__(self, client):
        self.client = client

    @classmethod
    def from_credentials(cls, *, access_key_id: str, secret_access_key: str):
        if not access_key_id or not secret_access_key:
            raise R2SnapshotError("R2 credentials missing")
        from boto3 import client  # optional runtime dependency
        from botocore.config import Config
        return cls(client(
            "s3", endpoint_url=R2_ENDPOINT, region_name="auto",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(signature_version="s3v4",
                          s3={"addressing_style": "path"},
                          retries={"max_attempts": 4, "mode": "standard"}),
        ))

    def put_file(self, key: str, source: Path, *, sha256: str) -> None:
        # S3-compatible upload_file uses managed multipart for large files.
        self.client.upload_file(str(source), R2_BUCKET, key,
                                ExtraArgs={"Metadata": {"sha256": sha256}})

    def put_bytes(self, key: str, body: bytes) -> None:
        self.client.put_object(Bucket=R2_BUCKET, Key=key,
                               Body=body, ContentType="application/json")

    def open(self, key: str) -> BinaryIO:
        return self.client.get_object(Bucket=R2_BUCKET, Key=key)["Body"]
