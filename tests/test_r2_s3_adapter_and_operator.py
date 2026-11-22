"""Check concrete S3 adapter arguments and fail-closed operator privileges."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from urano.r2_workspace_archive import Boto3R2Store, R2SnapshotError
from tools.r2_verify_project_roundtrip import _trusted_owner_registry


class FakeBoto3Client:
    def __init__(self):
        self.uploads = []
        self.writes = []
        self.reads = []

    def upload_file(self, filename, bucket, key, ExtraArgs=None):
        self.uploads.append((filename, bucket, key, ExtraArgs))

    def put_object(self, **kwargs):
        self.writes.append(kwargs)

    def get_object(self, **kwargs):
        self.reads.append(kwargs)
        return {"Body": io.BytesIO(b"native-input")}


class Boto3AdapterTests(unittest.TestCase):
    def test_real_s3_adapter_contract_for_bucket_and_checksum_metadata(self):
        conn = FakeBoto3Client()
        store = Boto3R2Store(conn)
        p = Path("/private/tests/sample.mp4")
        key = "tenants/pilot-amehc/snapshots/123/files/Projects/test.mp4"
        store.put_file(key, p, sha256="a" * 64)
        self.assertEqual(
            conn.uploads,
            [(str(p), "montara-media-eu-pilot", key,
              {"Metadata": {"sha256": "a" * 64}})],
        )
        store.put_bytes("tenants/pilot-amehc/manifest.json", b"{}")
        self.assertEqual(
            conn.writes[0]["Bucket"], "montara-media-eu-pilot")
        self.assertEqual(conn.writes[0]["ContentType"], "application/json")
        stream = store.open(key)
        self.assertEqual(stream.read(), b"native-input")
        self.assertEqual(conn.reads[0],
                         {"Bucket": "montara-media-eu-pilot", "Key": key})

    def test_missing_credentials_refused_before_constructing_s3_client(self):
        with self.assertRaises(R2SnapshotError):
            Boto3R2Store.from_credentials(access_key_id="", secret_access_key="")

    def test_trusted_owner_registry_must_be_private(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp).resolve() / "map.json"
            p.write_text(json.dumps({"owner": "pilot-amehc"}))
            p.chmod(0o644)
            with self.assertRaises(R2SnapshotError):
                _trusted_owner_registry(p)
            p.chmod(0o600)
            self.assertEqual(_trusted_owner_registry(p), {"owner": "pilot-amehc"})

    def test_untrusted_owner_registry_shape_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp).resolve() / "map.json"
            p.write_text(json.dumps(["pilot-amehc"]))
            p.chmod(0o600)
            with self.assertRaises(R2SnapshotError):
                _trusted_owner_registry(p)


if __name__ == "__main__":
    unittest.main()
