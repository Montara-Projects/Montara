import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from companion.outbound_presence import OutboundPresence
from urano.companion_pairing import CompanionPairing


class PairingTests(unittest.TestCase):
    def test_one_time_claim_and_owner_isolation(self):
        with tempfile.TemporaryDirectory() as temp:
            pairing = CompanionPairing(Path(temp) / "devices.db")
            code = pairing.invite("alice")
            with ThreadPoolExecutor(max_workers=4) as pool:
                claims = [result for result in pool.map(pairing.redeem, [code] * 4) if result]
            self.assertEqual(len(claims), 1)
            device = claims[0]
            self.assertEqual(pairing.online("alice"), [device["device"]])
            self.assertEqual(pairing.online("bob"), [])
            self.assertFalse(pairing.revoke("bob", device["device"]))
            self.assertTrue(pairing.heartbeat(device["token"]))
            self.assertTrue(pairing.revoke("alice", device["device"]))
            self.assertFalse(pairing.heartbeat(device["token"]))

    def test_invitation_expiry_and_reconnect(self):
        with tempfile.TemporaryDirectory() as temp:
            now = [1000]
            pairing = CompanionPairing(Path(temp) / "devices.db", now=lambda: now[0])
            expired = pairing.invite("alice")
            now[0] += 300
            self.assertIsNone(pairing.redeem(expired))
            device = pairing.redeem(pairing.invite("alice"))
            now[0] += 45
            self.assertEqual(pairing.online("alice"), [])
            self.assertTrue(pairing.heartbeat(device["token"]))
            self.assertEqual(pairing.online("alice"), [device["device"]])
            now[0] += 86400
            self.assertFalse(pairing.heartbeat(device["token"]))

    def test_native_client_rejects_insecure_or_ambiguous_origins(self):
        for origin in ("http://work.test", "https://person@work.test", "https://work.test/extra"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                OutboundPresence(origin)
