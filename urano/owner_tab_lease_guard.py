"""#369 — Broker-owned tab leases and atomic, fail-closed Engine-stop gate.

No privileged actions or timers occur in this module. Root broker must
authorize the OAuth session, CSRF, owner and project BEFORE using its methods.
No browser-provided completion or videoStatus value is an idle attestation.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import secrets
import time
from collections.abc import Callable

from urano.job_recovery_ledger import JobRecoveryLedger, JobLease

_HEX48 = re.compile(r"[0-9a-f]{48}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class TabLeaseDenied(PermissionError):
    pass


class EngineStillBusy(RuntimeError):
    pass


@dataclass(frozen=True)
class TrustedEngineIdle:
    """Created ONLY by an authorized native/Companion server-side inspector."""
    owner_id: str
    project_id: str
    generation: int
    local_mp4_verified: bool
    engine_tasks_idle: bool
    companion_render_idle: bool
    mixer_export_idle: bool

    def proves(self, job: JobLease) -> bool:
        return (
            self.owner_id == job.owner_id and
            self.project_id == job.project_id and
            type(self.generation) is int and self.generation == job.generation and
            all(type(value) is bool and value for value in (
                self.local_mp4_verified, self.engine_tasks_idle,
                self.companion_render_idle, self.mixer_export_idle,
            ))
        )


@dataclass(frozen=True)
class TabLeaseStatus:
    active_tabs: int
    in_flight_operations: int
    known_tabs: int
    can_consider_stopping: bool


class OwnerTabLeaseGuard:
    """Durable SQLite registry on the SAME DB used by the Owner job ledger.

    The broker passes a session hash derived from an independently verified
    private session; the user cannot select an Owner, project or generation.
    Browser tab tokens are opaque and scoped to that server-authenticated
    session + Owner + project + generation.
    """

    def __init__(self, ledger: JobRecoveryLedger, *, ttl_seconds=90,
                 grace_seconds=120):
        if not isinstance(ledger, JobRecoveryLedger):
            raise ValueError("Trusted JobRecoveryLedger required")
        if (type(ttl_seconds) is not int or not 30 <= ttl_seconds <= 600 or
                type(grace_seconds) is not int or not 30 <= grace_seconds <= 600):
            raise ValueError("Invalid lease timing")
        self.ledger = ledger
        self.ttl = ttl_seconds
        self.grace = grace_seconds
        with ledger._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS urano_owner_tabs(
                lease_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL,
                project_id TEXT NOT NULL, generation INTEGER NOT NULL,
                session_hash TEXT NOT NULL, issued_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL, released_at INTEGER)""")
            db.execute("""CREATE INDEX IF NOT EXISTS urano_tabs_generation
                ON urano_owner_tabs(owner_id,project_id,generation)""")
            db.execute("""CREATE TABLE IF NOT EXISTS urano_owner_tab_operations(
                operation_id TEXT PRIMARY KEY, lease_id TEXT NOT NULL,
                owner_id TEXT NOT NULL, project_id TEXT NOT NULL,
                generation INTEGER NOT NULL, started_at INTEGER NOT NULL)""")
            db.execute("""CREATE INDEX IF NOT EXISTS urano_tab_ops_generation
                ON urano_owner_tab_operations(owner_id,project_id,generation)""")

    @staticmethod
    def verified_session_hash(session: str) -> str:
        """ONLY after the broker has independently authenticated session+CSRF."""
        if type(session) is not str or not _HEX64.fullmatch(session):
            raise TabLeaseDenied("Unauthenticated session")
        return hashlib.sha256(session.encode("ascii")).hexdigest()

    @staticmethod
    def _identity(owner, project, generation, session_hash):
        if (type(generation) is not int or not 1 <= generation <= 2**31 - 1 or
                type(session_hash) is not str or not _HEX64.fullmatch(session_hash)):
            raise TabLeaseDenied("Unverified Owner generation or session")
        try:
            return (JobRecoveryLedger._principal(owner),
                    JobRecoveryLedger._principal(project), generation, session_hash)
        except (ValueError, TypeError) as exc:
            raise TabLeaseDenied("Invalid Owner/project identity") from exc

    @staticmethod
    def _token(value):
        if type(value) is not str or not _HEX48.fullmatch(value):
            raise TabLeaseDenied("Invalid opaque lease token")
        return value

    @staticmethod
    def _clock(now):
        if now is None:
            return int(time.time())
        if type(now) is not int or now < 1:
            raise ValueError("Invalid trusted time")
        return now

    @staticmethod
    def _running(db, owner, project, generation):
        row = db.execute("""SELECT owner_id,project_id,job_id,generation,state
            FROM urano_engine_jobs WHERE owner_id=? AND project_id=?
            AND generation=? AND state='running'""",
            (owner, project, generation)).fetchone()
        if row is None:
            raise TabLeaseDenied("Engine owner/generation not running")
        return JobLease(**dict(row))

    @staticmethod
    def _tab(db, token, owner, project, generation, session_hash):
        row = db.execute("""SELECT * FROM urano_owner_tabs WHERE lease_id=?
            AND owner_id=? AND project_id=? AND generation=? AND session_hash=?""",
            (token, owner, project, generation, session_hash)).fetchone()
        if row is None:
            raise TabLeaseDenied("Tab lease not owned by session")
        return row

    def _counts(self, db, owner, project, generation, now):
        active = db.execute("""SELECT COUNT(*) FROM urano_owner_tabs WHERE
            owner_id=? AND project_id=? AND generation=? AND released_at IS NULL
            AND expires_at+?>?""",
            (owner,project,generation,self.grace,now)).fetchone()[0]
        operations = db.execute("""SELECT COUNT(*) FROM urano_owner_tab_operations
            WHERE owner_id=? AND project_id=? AND generation=?""",
            (owner,project,generation)).fetchone()[0]
        known = db.execute("""SELECT COUNT(*) FROM urano_owner_tabs
            WHERE owner_id=? AND project_id=? AND generation=?""",
            (owner,project,generation)).fetchone()[0]
        return TabLeaseStatus(active,operations,known,
                              known > 0 and active == 0 and operations == 0)

    def open_tab(self, *, owner, project, generation, session_hash, now=None):
        owner,project,generation,session_hash = self._identity(
            owner,project,generation,session_hash)
        now=self._clock(now)
        with self.ledger._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._running(db,owner,project,generation)
            if self._counts(db,owner,project,generation,now).active_tabs >= 16:
                raise TabLeaseDenied("Too many simultaneous tabs")
            token=secrets.token_hex(24)
            db.execute("""INSERT INTO urano_owner_tabs
                (lease_id,owner_id,project_id,generation,session_hash,issued_at,expires_at)
                VALUES (?,?,?,?,?,?,?)""",
                (token,owner,project,generation,session_hash,now,now+self.ttl))
        return token

    def heartbeat(self, *, lease_id, owner, project, generation, session_hash, now=None):
        owner,project,generation,session_hash=self._identity(
            owner,project,generation,session_hash)
        lease_id=self._token(lease_id);now=self._clock(now)
        with self.ledger._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._running(db,owner,project,generation)
            row=self._tab(db,lease_id,owner,project,generation,session_hash)
            if row["released_at"] is not None or row["expires_at"] < now:
                raise TabLeaseDenied("Expired or released lease")
            expiration=now+self.ttl
            db.execute("UPDATE urano_owner_tabs SET expires_at=? WHERE lease_id=?",
                       (expiration,lease_id))
        return expiration

    def leave_tab(self, *, lease_id, owner, project, generation, session_hash,
                  now=None):
        """Idempotent: releases a tab, NEVER signals systemd."""
        owner,project,generation,session_hash=self._identity(
            owner,project,generation,session_hash)
        lease_id=self._token(lease_id);now=self._clock(now)
        with self.ledger._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=self._tab(db,lease_id,owner,project,generation,session_hash)
            if row["released_at"] is not None:
                return False
            db.execute("UPDATE urano_owner_tabs SET released_at=? WHERE lease_id=?",
                       (now,lease_id))
        return True

    def start_rpc(self, *, lease_id, owner, project, generation, session_hash, now=None):
        """Root broker records RPC before any private worker FD is granted."""
        owner,project,generation,session_hash=self._identity(
            owner,project,generation,session_hash)
        lease_id=self._token(lease_id);now=self._clock(now)
        with self.ledger._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._running(db,owner,project,generation)
            row=self._tab(db,lease_id,owner,project,generation,session_hash)
            if row["released_at"] is not None or row["expires_at"] < now:
                raise TabLeaseDenied("Inactive tab")
            op=secrets.token_hex(24)
            db.execute("""INSERT INTO urano_owner_tab_operations
                (operation_id,lease_id,owner_id,project_id,generation,started_at)
                VALUES (?,?,?,?,?,?)""",
                (op,lease_id,owner,project,generation,now))
            db.execute("UPDATE urano_owner_tabs SET expires_at=? WHERE lease_id=?",
                       (now+self.ttl,lease_id))
        return op

    def finish_rpc(self, *, operation_id, lease_id, owner, project,
                   generation, session_hash):
        """Server-side finally block; never accept unverified client exit."""
        owner,project,generation,session_hash=self._identity(
            owner,project,generation,session_hash)
        lease_id=self._token(lease_id);operation_id=self._token(operation_id)
        with self.ledger._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._tab(db,lease_id,owner,project,generation,session_hash)
            cursor=db.execute("""DELETE FROM urano_owner_tab_operations WHERE
                operation_id=? AND lease_id=? AND owner_id=? AND project_id=?
                AND generation=?""",
                (operation_id,lease_id,owner,project,generation))
            if cursor.rowcount:
                return True
            foreign=db.execute("""SELECT 1 FROM urano_owner_tab_operations
                WHERE operation_id=?""",(operation_id,)).fetchone()
            if foreign:
                raise TabLeaseDenied("Foreign in-flight operation")
        return False

    def snapshot(self, *, owner, project, generation, now=None):
        """Trusted read only; not authority for any stop."""
        with self.ledger._connect() as db:
            return self._counts(db,owner,project,generation,self._clock(now))

    def reserve_stop_after_verified_completion(self, *, owner, project,
                                               generation, trusted_probe=None, now=None):
        """Only authoritative root broker can call, with a SERVER idle probe.

        BEGIN IMMEDIATE makes this decision atomic with tab registration,
        heartbeat, RPC admission and the exact running -> stopping job state.
        Once reserved, subsequent tabs/RPCs fail closed. Actual shutdown
        still requires RestrictedTargetControl.stop_verified and cgroup proof.
        """
        if not callable(trusted_probe):
            raise EngineStillBusy("No trusted local completion/idle proof")
        now=self._clock(now)
        with self.ledger._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current=self._running(db,owner,project,generation)
            status=self._counts(db,owner,project,generation,now)
            if not status.can_consider_stopping:
                raise EngineStillBusy("Another active tab, RPC or no lease history")
            evidence=trusted_probe(current)
            if not isinstance(evidence,TrustedEngineIdle) or not evidence.proves(current):
                raise EngineStillBusy("Pending or unverified native/Companion work")
            changed=db.execute("""UPDATE urano_engine_jobs SET state='stopping'
                WHERE job_id=? AND owner_id=? AND project_id=? AND generation=?
                AND state='running'""",
                (current.job_id,owner,project,generation))
            if changed.rowcount != 1:
                raise EngineStillBusy("Concurrent generation change")
        return JobLease(owner,project,current.job_id,generation,"stopping")
