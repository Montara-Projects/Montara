import secrets
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from flask import Flask

from companion.outbound_presence import OutboundPresence
from urano.companion_pairing import CompanionPairing
from urano.companion_pairing_http import companion_pairing_blueprint
from urano.companion_proof import encode, heartbeat_message
from urano.session_auth import SESSION_COOKIE, SessionStore


class PairingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.now = 1000
        self.pairing = CompanionPairing(self.root / "devices.db", now=lambda: self.now)
        self.key = Ed25519PrivateKey.generate()
        self.public = encode(self.key.public_key().public_bytes_raw())

    def proof(self, token, key=None):
        nonce = encode(secrets.token_bytes(16))
        signature = (key or self.key).sign(heartbeat_message(token, self.now, nonce))
        return dict(timestamp=self.now, nonce=nonce, proof=encode(signature))

    def test_one_time_claim_and_owner_isolation(self):
        code = self.pairing.invite("alice")
        with ThreadPoolExecutor(max_workers=4) as pool:
            claims = list(pool.map(lambda _: self.pairing.redeem(code, self.public), range(4)))
        device, = filter(None, claims)
        self.assertEqual(self.pairing.online("alice"), [])
        token = device["token"]
        self.assertFalse(self.pairing.heartbeat(token, **self.proof(token, Ed25519PrivateKey.generate())))
        proof = self.proof(token)
        self.assertTrue(self.pairing.heartbeat(token, **proof))
        self.assertFalse(self.pairing.heartbeat(token, **proof))
        self.assertEqual(self.pairing.online("alice"), [device["device"]])
        self.assertEqual(self.pairing.online("bob"), [])
        self.assertFalse(self.pairing.revoke("bob", device["device"]))
        self.assertTrue(self.pairing.revoke("alice", device["device"]))
        self.assertFalse(self.pairing.heartbeat(token, **self.proof(token)))

    def test_expiry_and_reconnect(self):
        code = self.pairing.invite("alice")
        self.now += 300
        self.assertIsNone(self.pairing.redeem(code, self.public))
        device = self.pairing.redeem(self.pairing.invite("alice"), self.public)
        proof = self.proof(device["token"])
        self.now += 45
        self.assertFalse(self.pairing.heartbeat(device["token"], **proof))
        self.assertTrue(self.pairing.heartbeat(device["token"], **self.proof(device["token"])))
        self.assertEqual(self.pairing.online("alice"), [device["device"]])
        self.now += 86400
        self.assertFalse(self.pairing.heartbeat(device["token"], **self.proof(device["token"])))

    def test_http_pairing_uses_owner_session_and_csrf(self):
        origin = "https://work.test"
        base = "/urano/v1/companion/"
        sessions = SessionStore(self.root / "sessions.db")
        app = Flask(__name__)
        app.register_blueprint(companion_pairing_blueprint(sessions, self.pairing, origin=origin))
        owner, native = app.test_client(), app.test_client()
        session = sessions.issue("alice")
        owner.set_cookie(SESSION_COOKIE, session.token, domain="work.test")
        self.assertEqual(owner.post(base + "invite", base_url=origin).status_code, 403)
        response = owner.post(base + "invite", base_url=origin,
                              headers={"Origin": origin, "X-Urano-CSRF": session.csrf})
        self.assertEqual(response.status_code, 201)
        redeemed = native.post(base + "redeem", base_url=origin,
                               json={"code": response.json["code"], "public_key": self.public})
        token = redeemed.json["token"]
        request = dict(base_url=origin, headers={"Authorization": "Bearer " + token},
                       json=self.proof(token))
        self.assertEqual(native.post(base + "heartbeat", **request).status_code, 204)
        self.assertEqual(native.post(base + "heartbeat", **request).status_code, 401)
        self.assertEqual(owner.get(base + "devices", base_url=origin).json,
                         {"online": [redeemed.json["device"]]})
        self.assertEqual(native.get(base + "devices", base_url=origin).status_code, 401)

    def test_native_client_rejects_insecure_or_ambiguous_origins(self):
        for origin in ("http://work.test", "https://person@work.test", "https://work.test/extra"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                OutboundPresence(origin)
