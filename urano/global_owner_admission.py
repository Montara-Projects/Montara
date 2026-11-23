"""Shared, operator-only FIFO admission ledger across H4 isolated brokers.

All broker processes must be explicitly configured to use the SAME trusted
root-owned SQLite path; no HTTP caller may choose the ledger location.
Admission does not launch/stop processes. The broker MUST hold the reservation
through its unverified/stopping/orphaned cgroup states; release requires an
independent verified-empty cgroup assertion from trusted control plane.

Queue status is public only for the authenticated owner via broker policy;
never return other owners' IDs, project paths, worker names or reservations.
"""
from __future__ import annotations

import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

OWNER=re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
JOB=re.compile(r"job-[a-f0-9]{32}\Z")
STATE=("queued","reserved","running","stopping","orphaned","released","cancelled")


class GlobalAdmissionDenied(RuntimeError):
    """The operator-wide admission ledger is unavailable or invalid."""


@dataclass(frozen=True)
class Admission:
    state: str
    position: int | None
    capacity_gib: int
    reserved_gib: int
    request_id: str


class GlobalOwnerAdmission:
    """Atomic SQLite FIFO, RAM reservations and one admitted job per owner.

    Allocation is serialized with BEGIN IMMEDIATE, including different
    broker processes and H4 namespaces. Owner fairness is enforced by a
    UNIQUE constraint on admitted owner rows. Deliberately no ETA: a
    duration estimate must be derived from empirical successful jobs.
    """

    def __init__(self, path: str | Path, *, capacity_gib: int = 24):
        self.path=Path(path)
        if (type(capacity_gib) is not int or not 1<=capacity_gib<=1024
                or not self.path.is_absolute() or self.path.is_symlink()
                or not self.path.parent.is_dir()):
            raise GlobalAdmissionDenied("Invalid trusted global admission config")
        self.capacity_gib=capacity_gib
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS global_owner_admission(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE NOT NULL,
                owner_id TEXT NOT NULL,
                instance TEXT NOT NULL,
                requested_gib INTEGER NOT NULL,
                state TEXT NOT NULL CHECK(state IN
                ('queued','reserved','running','stopping','orphaned','released','cancelled')),
                inserted_at REAL NOT NULL)""")
            # Many queued renders per Owner are allowed, but only ONE may
            # consume RAM at a time. This prevents a prolific Owner from
            # taking several shares ahead of other Owners.
            db.execute("DROP INDEX IF EXISTS one_active_admission_per_owner")
            db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS one_running_admission_per_owner
                ON global_owner_admission(owner_id)
                WHERE state IN ('reserved','running','stopping','orphaned')""")

    def connect(self):
        db=sqlite3.connect(str(self.path),timeout=10,isolation_level=None)
        db.row_factory=sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    @staticmethod
    def validate(owner,request_id,instance,needed):
        if (not isinstance(owner,str) or not OWNER.fullmatch(owner)
                or not isinstance(request_id,str) or not JOB.fullmatch(request_id)
                or instance not in ("jmlab","main","fertrial","betamain")
                or type(needed) is not int or not 1<=needed<=64):
            raise GlobalAdmissionDenied("Invalid trusted reservation")

    def ask(self, owner, request_id, instance, needed_gib) -> Admission:
        self.validate(owner,request_id,instance,needed_gib)
        if needed_gib>self.capacity_gib:
            raise GlobalAdmissionDenied("Worker reservation larger than total budget")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing=db.execute("""SELECT * FROM global_owner_admission
                WHERE request_id=?""",(request_id,)).fetchone()
            if existing:
                if (existing["owner_id"]!=owner
                    or existing["requested_gib"]!=needed_gib
                    or existing["instance"]!=instance
                    or existing["state"] not in ('queued','reserved','running','stopping','orphaned')):
                    raise GlobalAdmissionDenied("Foreign, stale or changed reservation")
            else:
                pending=db.execute("""SELECT COUNT(*) FROM global_owner_admission
                    WHERE owner_id=? AND state='queued'""",(owner,)).fetchone()[0]
                if pending>=8:
                    raise GlobalAdmissionDenied("Owner queue limit exceeded")
                db.execute("""INSERT INTO global_owner_admission
                    (request_id,owner_id,instance,requested_gib,state,inserted_at)
                    VALUES (?,?,?,?,?,?)""",
                    (request_id,owner,instance,needed_gib,"queued",time.time()))
            return self._promote_and_status(db,request_id)

    def _promote_and_status(self,db,request_id):
        # Head-of-line FIFO and reserved RAM, not CPU shares, gate
        # admission. Never silently bypass a large older queued request.
        reservations=db.execute("""SELECT COALESCE(SUM(requested_gib),0) AS n
            FROM global_owner_admission WHERE state IN
            ('reserved','running','stopping','orphaned')""").fetchone()["n"]
        busy_owners={row["owner_id"] for row in db.execute("""SELECT owner_id
            FROM global_owner_admission WHERE state IN
            ('reserved','running','stopping','orphaned')""").fetchall()}
        pending=db.execute("""SELECT seq, request_id, owner_id, requested_gib
            FROM global_owner_admission WHERE state='queued'
            ORDER BY seq""").fetchall()
        available=self.capacity_gib-reservations
        for row in pending:
            if row["owner_id"] in busy_owners:
                # One Owner's additional queued render cannot block a
                # different Owner who still has an available RAM slot.
                continue
            if row["requested_gib"]>available:
                break
            db.execute("""UPDATE global_owner_admission SET state='reserved'
                WHERE request_id=? AND state='queued'""",(row["request_id"],))
            available-=row["requested_gib"]
            busy_owners.add(row["owner_id"])
        record=db.execute("""SELECT seq,state FROM global_owner_admission
            WHERE request_id=?""",(request_id,)).fetchone()
        if record is None:
            raise GlobalAdmissionDenied("Unknown admission request")
        queue=db.execute("""SELECT seq FROM global_owner_admission
            WHERE state='queued' ORDER BY seq""").fetchall()
        position=next((i for i,row in enumerate(queue,1)
                       if row["seq"]==record["seq"]),None)
        return Admission(record["state"],position,self.capacity_gib,
                         self.capacity_gib-available,request_id)

    def status(self,request_id,owner)->Admission:
        if not isinstance(owner,str) or not OWNER.fullmatch(owner):
            raise GlobalAdmissionDenied("Invalid owner")
        if not isinstance(request_id,str) or not JOB.fullmatch(request_id):
            raise GlobalAdmissionDenied("Invalid request")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("""SELECT owner_id FROM global_owner_admission
                WHERE request_id=?""",(request_id,)).fetchone()
            if row is None or row["owner_id"]!=owner:
                raise GlobalAdmissionDenied("Not owner of queued job")
            return self._promote_and_status(db,request_id)

    def mark_running(self,request_id,owner):
        return self._change(request_id,owner,("reserved",),"running")

    def mark_stopping(self,request_id,owner):
        return self._change(request_id,owner,("reserved","running","orphaned"),"stopping")

    def mark_orphaned(self,request_id,owner):
        return self._change(request_id,owner,("reserved","running","stopping"),"orphaned")

    def cancel_queued(self,request_id,owner):
        return self._change(request_id,owner,("queued",),"cancelled")

    def release_verified(self,request_id,owner,*,cgroup_verified_empty=False):
        if cgroup_verified_empty is not True:
            raise GlobalAdmissionDenied("Verified-empty cgroup required")
        return self._change(request_id,owner,
                            ("reserved","running","stopping","orphaned"),"released")

    def _change(self,request_id,owner,old,new):
        if not isinstance(owner,str) or not OWNER.fullmatch(owner):
            raise GlobalAdmissionDenied("Invalid owner")
        if not isinstance(request_id,str) or not JOB.fullmatch(request_id):
            raise GlobalAdmissionDenied("Invalid request")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("""SELECT state,owner_id FROM global_owner_admission
                WHERE request_id=?""",(request_id,)).fetchone()
            if row is None or row["owner_id"]!=owner or row["state"] not in old:
                raise GlobalAdmissionDenied("Stale or foreign admission transition")
            db.execute("UPDATE global_owner_admission SET state=? WHERE request_id=?",
                       (new,request_id))
            return new
