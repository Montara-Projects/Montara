"""Persistent, owner-scoped render leases for the outbound Companion pilot."""
import re
import secrets
from contextlib import closing

from urano.project_catalog import ProjectNotFound


class JobConflict(ValueError):
    pass


class CompanionJobs:
    def __init__(self, pairing, catalog):
        self.pairing = pairing
        self.catalog = catalog
        with closing(pairing.connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS companion_render_jobs (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, project TEXT NOT NULL,
                device TEXT NOT NULL, request_id TEXT NOT NULL, expires REAL NOT NULL,
                state TEXT NOT NULL, lease TEXT, lease_until REAL,
                progress INTEGER NOT NULL DEFAULT 0,
                UNIQUE(owner, request_id)
            )""")
            db.execute("""CREATE INDEX IF NOT EXISTS companion_render_device
                        ON companion_render_jobs(device, state, expires)""")

    def create(self, owner, project, device, request_id):
        if not isinstance(request_id, str) or not re.fullmatch(r"[a-f0-9]{32}", request_id):
            raise ValueError("Invalid request identifier")
        self.catalog.get(owner, project)
        now = self.pairing.now()
        with closing(self.pairing.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute("SELECT 1 FROM devices WHERE id=? AND owner=? AND expires>?",
                              (device, owner, now)).fetchone():
                raise ProjectNotFound("Device not found")
            existing = db.execute("""SELECT id, project, device FROM companion_render_jobs
                                     WHERE owner=? AND request_id=?""", (owner, request_id)).fetchone()
            if existing:
                if existing[1:] != (project, device):
                    raise JobConflict("Request identifier was already used")
                return existing[0]
            if db.execute("""SELECT count(*) FROM companion_render_jobs
                             WHERE owner=? AND state IN ('pending','running') AND expires>?""",
                          (owner, now)).fetchone()[0] >= 4:
                raise JobConflict("Render queue is full")
            job = secrets.token_hex(16)
            db.execute("""INSERT INTO companion_render_jobs
                          (id, owner, project, device, request_id, expires, state)
                          VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
                       (job, owner, project, device, request_id, now+3600))
            return job

    def status(self, owner, project, job):
        self.catalog.get(owner, project)
        with closing(self.pairing.connect()) as db:
            row = db.execute("""SELECT state, progress, expires FROM companion_render_jobs
                                WHERE id=? AND project=? AND owner=?""", (job, project, owner)).fetchone()
        if row is None:
            raise ProjectNotFound("Job not found")
        state = "expired" if row[0] in ("pending", "running") and row[2] <= self.pairing.now() else row[0]
        return {"state": state, "progress": row[1]}

    def cancel(self, owner, project, job):
        self.catalog.get(owner, project)
        with closing(self.pairing.connect()) as db, db:
            return db.execute("""UPDATE companion_render_jobs SET state='cancelled'
                                 WHERE id=? AND project=? AND owner=?
                                 AND state IN ('pending','running') AND expires>?""",
                              (job, project, owner, self.pairing.now())).rowcount == 1

    def claim(self, db, owner, device):
        """Called inside the verified, single-use device request transaction."""
        now = self.pairing.now()
        db.execute("""UPDATE companion_render_jobs SET state='pending', lease=NULL,
                      lease_until=NULL, progress=0
                      WHERE device=? AND owner=? AND state='running' AND lease_until<=?""",
                   (device, owner, now))
        if db.execute("""SELECT 1 FROM companion_render_jobs
                         WHERE device=? AND owner=? AND state='running' AND expires>?""",
                      (device, owner, now)).fetchone():
            return None
        row = db.execute("""SELECT id, project FROM companion_render_jobs
                            WHERE device=? AND owner=? AND state='pending' AND expires>?
                            ORDER BY rowid LIMIT 1""", (device, owner, now)).fetchone()
        if row is None:
            return None
        lease = secrets.token_hex(16)
        db.execute("""UPDATE companion_render_jobs SET state='running', lease=?, lease_until=?
                      WHERE id=?""", (lease, now+60, row[0]))
        return {"id": row[0], "project": row[1], "operation": "render_video", "lease": lease}

    def progress(self, db, owner, device, job, lease, value):
        if type(value) is not int or not 0 <= value <= 100:
            raise ValueError("Invalid progress")
        now = self.pairing.now()
        return db.execute("""UPDATE companion_render_jobs SET progress=max(progress, ?), lease_until=?
                             WHERE id=? AND owner=? AND device=? AND lease=? AND state='running'
                             AND lease_until>? AND expires>?""",
                          (value, now+60, job, owner, device, lease, now, now)).rowcount == 1
