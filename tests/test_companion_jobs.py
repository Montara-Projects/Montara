import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from urano.companion_jobs import CompanionJobs
from urano.companion_pairing import CompanionPairing
from urano.companion_proof import encode, job_message
from urano.project_catalog import ProjectCatalog, ProjectNotFound


class CompanionJobTests(unittest.TestCase):
    def test_isolation_idempotency_restart_and_cancel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            now = [1000]
            pairing = CompanionPairing(root / "devices.db", now=lambda: now[0])
            catalog = ProjectCatalog(root / "projects.db")
            jobs = CompanionJobs(pairing, catalog)
            key = Ed25519PrivateKey.generate()
            device = pairing.redeem(pairing.invite("alice"),
                                    encode(key.public_key().public_bytes_raw()))
            token = device["token"]
            project = catalog.create("alice", "Synthetic").id
            foreign = catalog.create("bob", "Foreign").id
            request_id = "a" * 32
            job = jobs.create("alice", project, device["device"], request_id)
            self.assertEqual(jobs.create("alice", project, device["device"], request_id), job)
            with self.assertRaises(ProjectNotFound):
                jobs.create("alice", foreign, device["device"], request_id)
            with self.assertRaises(ProjectNotFound):
                jobs.status("bob", foreign, job)

            def signed(operation, payload, action, serial, mutate=None):
                nonce = encode(serial.to_bytes(16, "big"))
                signature = encode(key.sign(job_message(token, now[0], nonce, operation, payload)))
                return pairing.device_request(token, now[0], nonce, signature,
                    operation=operation, payload=mutate if mutate is not None else payload,
                    action=action)

            accepted, lease = signed("claim", {}, jobs.claim, 1)
            self.assertTrue(accepted)
            self.assertEqual(lease["id"], job)
            self.assertEqual(signed("claim", {}, jobs.claim, 1), (False, None))
            self.assertEqual(signed("claim", {}, jobs.claim, 2), (True, None))
            now[0] += 61
            jobs = CompanionJobs(pairing, catalog)
            _, restarted = signed("claim", {}, jobs.claim, 3)
            self.assertNotEqual(lease["lease"], restarted["lease"])

            def report(db, owner, device):
                return jobs.progress(db, owner, device, job, restarted["lease"], 20)

            self.assertEqual(signed("progress", {"value": 20}, report, 4,
                                    mutate={"value": 90}), (False, None))
            self.assertEqual(signed("progress", {"value": 20}, report, 4), (True, True))
            self.assertEqual(jobs.status("alice", project, job)["progress"], 20)
            self.assertFalse(jobs.cancel("bob", foreign, job))
            self.assertTrue(jobs.cancel("alice", project, job))
            self.assertEqual(signed("progress", {"value": 20}, report, 5), (True, False))
