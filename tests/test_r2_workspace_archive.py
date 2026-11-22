"""Roundtrip a complete native project through an in-memory S3 test double.

These integration tests use Montara's original core.project loader if its
engine submodule is available. They do NOT claim a live Cloudflare E2E.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

from urano.r2_workspace_archive import (
    R2SnapshotError, snapshot_workspace, verify_snapshot, restore_workspace,
    prepare_editor_scratch,
)

try:
    from core.project import create_project, load_project, file_record
except ImportError:
    create_project = load_project = file_record = None


class FakeR2:
    def __init__(self):
        self.objects = {}
        self.uploads = 0

    def put_file(self, key, source, *, sha256):
        data = Path(source).read_bytes()
        assert hashlib.sha256(data).hexdigest() == sha256
        self.objects[key] = data
        self.uploads += 1

    def put_bytes(self, key, body):
        self.objects[key] = body

    def open(self, key):
        return io.BytesIO(self.objects[key])


class R2WorkspaceRoundtripTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.root = self.base / "owner"
        self.root.mkdir(mode=0o700)
        self.project = self.root / "Projects" / "Concert.zuckervid"
        self.project.mkdir(parents=True)
        (self.project / "inputs" / "videos").mkdir(parents=True)
        (self.project / "artifacts").mkdir(parents=True)
        (self.project / "artifacts" / "edit_plan.json").write_text(
            '{"shots":[{"camera":"left"}]}', encoding="utf8")
        (self.project / "library" / "assets").mkdir(parents=True)
        (self.project / "library" / "assets" / "still.jpg").write_bytes(
            b"\xff\xd8" + b"montara-private-still" * 50)
        self.upload = self.root / "Uploads" / ("1" * 32) / "show.mp4"
        self.upload.parent.mkdir(parents=True)
        self.upload.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"test-concert-bytes" * 500)
        (self.root / "Sessions" / "123456789abc").mkdir(parents=True)
        (self.root / "Sessions" / "123456789abc" / "session.json").write_text(
            json.dumps({"id": "123456789abc", "path": str(self.upload)}),
            encoding="utf8")
        (self.root / "config.json").write_text(
            json.dumps({"project_root": str(self.root / "Projects")}),
            encoding="utf8")
        if create_project:
            project = create_project("Concert", str(self.project))
            project.set_videos([str(self.upload)])
            self.assertEqual(project.data["inputs"]["videos"][0]["path"], str(self.upload))
        else:
            (self.project / "project.json").write_text(
                json.dumps({"schema_version": 1, "name": "Concert",
                            "inputs": {"videos": [{"path": str(self.upload)}]}}),
                encoding="utf8")
        self.owner_tenants = {"verified-owner": "pilot-amehc"}
        self.store = FakeR2()

    def snapshot(self, **kwargs):
        arguments = dict(root=self.root, store=self.store, trusted_instance="jmlab",
                         verified_owner_id="verified-owner",
                         owner_tenants=self.owner_tenants)
        arguments.update(kwargs)
        return snapshot_workspace(**arguments)

    def test_full_roundtrip_and_native_project_opened_from_restored_r2(self):
        before = {
            str(p.relative_to(self.root)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in self.root.rglob("*") if p.is_file()
        }
        receipt = self.snapshot()
        self.assertGreaterEqual(receipt.files, 5)
        self.assertTrue(receipt.manifest_key.startswith("tenants/pilot-amehc/"))
        checked = verify_snapshot(store=self.store, tenant=receipt.tenant,
                                  snapshot_id=receipt.snapshot_id)
        self.assertEqual(receipt, checked)
        # Simulate source no longer available. Rehydrate to the SAME trusted
        # root, so absolute native input paths remain resolvable.
        offline = self.base / "owner.original-not-used"
        self.root.rename(offline)
        restored = restore_workspace(
            store=self.store, tenant=receipt.tenant,
            snapshot_id=receipt.snapshot_id, destination=self.root,
            expected_manifest_sha256=receipt.sha256)
        self.assertEqual(receipt, restored)
        for path, (raw, stamp) in before.items():
            fresh = self.root / path
            self.assertEqual(raw, fresh.read_bytes(), path)
            self.assertEqual(stamp, fresh.stat().st_mtime_ns, path)
        self.assertTrue(self.upload.is_file())
        if load_project:
            reopened = load_project(str(self.project))
            self.assertEqual(reopened.data["name"], "Concert")
            self.assertEqual(reopened.data["inputs"]["videos"][0]["path"],
                             str(self.upload))
            self.assertTrue(Path(reopened.data["inputs"]["videos"][0]["path"]).is_file())
            self.assertEqual(json.loads(
                (reopened.folder / "artifacts" / "edit_plan.json").read_text()
            )["shots"][0]["camera"], "left")

    def test_open_r2_materialized_project_without_originals_and_rebound_paths(self):
        receipt = self.snapshot()
        new_root = self.base / "r2-scratch"
        restore_workspace(
            store=self.store, tenant=receipt.tenant,
            snapshot_id=receipt.snapshot_id, destination=new_root,
            expected_manifest_sha256=receipt.sha256)
        source_offline = self.base / "source-offline"
        self.root.rename(source_offline)
        changes = prepare_editor_scratch(
            store=self.store, tenant=receipt.tenant,
            snapshot_id=receipt.snapshot_id,
            expected_manifest_sha256=receipt.sha256, restored_root=new_root)
        self.assertGreaterEqual(changes, 1)
        cloud_project = new_root / "Projects" / "Concert.zuckervid"
        scratch_config = json.loads((new_root / "config.json").read_text())
        self.assertEqual(scratch_config["project_root"], str(new_root / "Projects"))
        scratch_session = json.loads((new_root / "Sessions" /
             "123456789abc" / "session.json").read_text())
        self.assertEqual(scratch_session["path"],
                         str(new_root / "Uploads" / ("1" * 32) / "show.mp4"))
        if load_project:
            reopened = load_project(str(cloud_project))
            video = Path(reopened.data["inputs"]["videos"][0]["path"])
            self.assertTrue(video.is_file())
            self.assertTrue(video.is_relative_to(new_root))
            self.assertFalse(video.is_relative_to(source_offline))
        # The canonical files and receipt stored in R2 remain unchanged.
        self.assertEqual(receipt, verify_snapshot(
            store=self.store, tenant=receipt.tenant,
            snapshot_id=receipt.snapshot_id))

    def test_scratch_rebind_fails_when_original_reference_not_backed_up(self):
        receipt = self.snapshot()
        new_root = self.base / "r2-scratch"
        restore_workspace(
            store=self.store, tenant=receipt.tenant,
            snapshot_id=receipt.snapshot_id, destination=new_root,
            expected_manifest_sha256=receipt.sha256)
        video = new_root / "Uploads" / ("1" * 32) / "show.mp4"
        video.unlink()
        with self.assertRaises(R2SnapshotError):
            prepare_editor_scratch(
                store=self.store, tenant=receipt.tenant,
                snapshot_id=receipt.snapshot_id,
                expected_manifest_sha256=receipt.sha256, restored_root=new_root)

    def test_hash_mismatch_refuses_snapshot_commit(self):
        class AlteredR2(FakeR2):
            def put_file(self, key, source, *, sha256):
                super().put_file(key, source, sha256=sha256)
                self.objects[key] += b"corruption"
        self.store = AlteredR2()
        with self.assertRaisesRegex(R2SnapshotError, "hash mismatch"):
            self.snapshot()
        self.assertFalse(any(x.endswith("manifest.json") for x in self.store.objects))
        self.assertTrue(self.project.is_dir())

    def test_corrupted_remote_object_refuses_validation_and_restore(self):
        receipt = self.snapshot()
        object_key = next(x for x in self.store.objects if x.endswith("show.mp4"))
        self.store.objects[object_key] = b"bad"
        with self.assertRaises(R2SnapshotError):
            verify_snapshot(store=self.store, tenant=receipt.tenant,
                            snapshot_id=receipt.snapshot_id)
        target = self.base / "restored"
        with self.assertRaises(R2SnapshotError):
            restore_workspace(store=self.store, tenant=receipt.tenant,
                              snapshot_id=receipt.snapshot_id, destination=target,
                              expected_manifest_sha256=receipt.sha256)
        self.assertFalse(target.exists())
        self.assertTrue(self.upload.is_file())

    def test_foreign_tenant_access_denied(self):
        with self.assertRaises(R2SnapshotError):
            self.snapshot(trusted_instance="fertrial")
        with self.assertRaises(R2SnapshotError):
            self.snapshot(owner_tenants={"verified-owner": "pilot-t4t"})
        self.assertFalse(self.store.objects)

    def test_restore_does_not_overwrite_existing_source(self):
        receipt = self.snapshot()
        with self.assertRaises(R2SnapshotError):
            restore_workspace(store=self.store, tenant=receipt.tenant,
                              snapshot_id=receipt.snapshot_id, destination=self.root,
            expected_manifest_sha256=receipt.sha256)
        self.assertTrue(self.upload.is_file())

    def test_linked_media_or_directory_rejected(self):
        external = self.base / "outside.mp4"
        external.write_bytes(b"outside")
        linked = self.root / "Projects" / "link"
        linked.symlink_to(external)
        with self.assertRaisesRegex(R2SnapshotError, "linked|Linked"):
            self.snapshot()
        linked.unlink()
        linked_dir = self.root / "Projects" / "external"
        linked_dir.symlink_to(self.base, target_is_directory=True)
        with self.assertRaisesRegex(R2SnapshotError, "Linked"):
            self.snapshot()

    def test_mutated_original_after_upload_never_commits(self):
        class MutatingR2(FakeR2):
            def put_file(self, key, source, *, sha256):
                super().put_file(key, source, sha256=sha256)
                Path(source).write_bytes(Path(source).read_bytes() + b"mutation")
        self.store = MutatingR2()
        with self.assertRaisesRegex(R2SnapshotError, "changed during upload"):
            self.snapshot()
        self.assertFalse(any(x.endswith("manifest.json") for x in self.store.objects))

    def test_manipulated_manifest_path_denied(self):
        receipt = self.snapshot()
        obj = json.loads(self.store.objects[receipt.manifest_key])
        obj["files"][0]["path"] = "../../etc/passwd"
        self.store.objects[receipt.manifest_key] = json.dumps(obj).encode()
        target = self.base / "restored"
        with self.assertRaises(R2SnapshotError):
            restore_workspace(store=self.store, tenant=receipt.tenant,
                              snapshot_id=receipt.snapshot_id, destination=target,
                              expected_manifest_sha256=receipt.sha256)
        self.assertFalse(target.exists())

    def test_wrong_bucket_or_tenant_manifest_denied(self):
        receipt = self.snapshot()
        obj = json.loads(self.store.objects[receipt.manifest_key])
        obj["jurisdiction"] = "default"
        self.store.objects[receipt.manifest_key] = json.dumps(obj).encode()
        with self.assertRaises(R2SnapshotError):
            verify_snapshot(store=self.store, tenant=receipt.tenant,
                            snapshot_id=receipt.snapshot_id)

    def test_no_project_never_committed(self):
        (self.project / "project.json").unlink()
        with self.assertRaisesRegex(R2SnapshotError, "No saved native project"):
            self.snapshot()
        self.assertFalse(any(x.endswith("manifest.json") for x in self.store.objects))

    def test_bad_snapshot_id_rejected(self):
        with self.assertRaises(R2SnapshotError):
            self.snapshot(snapshot_id="../bad")


if __name__ == "__main__":
    unittest.main()
