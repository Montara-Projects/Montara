"""Owner-scoped, outbound-only Companion presence prototype."""
import hashlib
import re
import secrets
import sqlite3
import time
from contextlib import closing

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from urano.companion_proof import decode, heartbeat_message


def digest(secret):
    return hashlib.sha256(secret.encode("ascii")).hexdigest()


class CompanionPairing:
    def __init__(self, path, *, now=time.time):
        self.path = path
        self.now = now
        with closing(self.connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS invitations (
                    code TEXT PRIMARY KEY, owner TEXT NOT NULL, expires REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, token TEXT UNIQUE NOT NULL,
                    expires REAL NOT NULL, seen REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS device_keys (
                    device TEXT PRIMARY KEY REFERENCES devices(id) ON DELETE CASCADE,
                    public_key BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS heartbeat_nonces (
                    device TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                    nonce TEXT NOT NULL, expires REAL NOT NULL,
                    PRIMARY KEY(device, nonce)
                );
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def invite(self, owner):
        code = secrets.token_urlsafe(24)
        with closing(self.connect()) as db, db:
            db.execute("DELETE FROM invitations WHERE expires<=? OR owner=?", (self.now(), owner))
            db.execute("INSERT INTO invitations VALUES (?,?,?)", (digest(code), owner, self.now()+300))
        return code

    def redeem(self, code, public_key):
        if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{32}", code):
            return None
        key = decode(public_key, 32)
        if key is None:
            return None
        token, device = secrets.token_urlsafe(32), secrets.token_hex(16)
        now = self.now()
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("DELETE FROM invitations WHERE code=? AND expires>? RETURNING owner",
                             (digest(code), now)).fetchone()
            if row is None:
                return None
            db.execute("DELETE FROM devices WHERE expires<=?", (now,))
            db.execute("INSERT INTO devices VALUES (?,?,?,?,?)",
                       (device, row[0], digest(token), now+86400, 0))
            db.execute("INSERT INTO device_keys VALUES (?,?)", (device, key))
        return {"device": device, "token": token}

    def heartbeat(self, token, timestamp, nonce, proof):
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            return False
        now = self.now()
        signature = decode(proof, 64)
        if (type(timestamp) is not int or abs(timestamp-now) > 30 or
                decode(nonce, 16) is None or signature is None):
            return False
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""SELECT d.id, k.public_key FROM devices d
                                JOIN device_keys k ON k.device=d.id
                                WHERE d.token=? AND d.expires>?""", (digest(token), now)).fetchone()
            if row is None:
                return False
            try:
                Ed25519PublicKey.from_public_bytes(row[1]).verify(
                    signature, heartbeat_message(token, timestamp, nonce))
            except InvalidSignature:
                return False
            db.execute("DELETE FROM heartbeat_nonces WHERE expires<?", (now,))
            if not db.execute("INSERT OR IGNORE INTO heartbeat_nonces VALUES (?,?,?)",
                              (row[0], nonce, timestamp+30)).rowcount:
                return False
            db.execute("UPDATE devices SET seen=? WHERE id=?", (now, row[0]))
            return True

    def online(self, owner):
        now = self.now()
        with closing(self.connect()) as db:
            return [row[0] for row in db.execute(
                "SELECT id FROM devices JOIN device_keys ON device_keys.device=devices.id WHERE owner=? AND expires>? AND seen>? AND seen>0",
                (owner, now, now-45))]

    def revoke(self, owner, device):
        with closing(self.connect()) as db, db:
            return db.execute("DELETE FROM devices WHERE owner=? AND id=?",
                              (owner, device)).rowcount == 1
