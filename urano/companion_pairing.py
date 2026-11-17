"""Owner-scoped, outbound-only Companion presence prototype."""
import hashlib
import re
import secrets
import sqlite3
import time
from contextlib import closing


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
            """)

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def invite(self, owner):
        code = secrets.token_urlsafe(24)
        with closing(self.connect()) as db, db:
            db.execute("DELETE FROM invitations WHERE expires<=? OR owner=?", (self.now(), owner))
            db.execute("INSERT INTO invitations VALUES (?,?,?)", (digest(code), owner, self.now()+300))
        return code

    def redeem(self, code):
        if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{32}", code):
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
                       (device, row[0], digest(token), now+86400, now))
        return {"device": device, "token": token}

    def heartbeat(self, token):
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            return False
        now = self.now()
        with closing(self.connect()) as db, db:
            return db.execute("UPDATE devices SET seen=? WHERE token=? AND expires>?",
                              (now, digest(token), now)).rowcount == 1

    def online(self, owner):
        now = self.now()
        with closing(self.connect()) as db:
            return [row[0] for row in db.execute(
                "SELECT id FROM devices WHERE owner=? AND expires>? AND seen>?",
                (owner, now, now-45))]

    def revoke(self, owner, device):
        with closing(self.connect()) as db, db:
            return db.execute("DELETE FROM devices WHERE owner=? AND id=?",
                              (owner, device)).rowcount == 1
