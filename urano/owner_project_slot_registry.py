"""#380: server-owned canonical project identities, unique titles and CAS saves.

This is a *metadata gate*, not the Engine file writer. The trusted Owner
service must verify session+CSRF before invoking a mutation; a native Engine
must independently verify the Owner's path and finish a durable file write
before calling commit_snapshot. Never expose bind_video_path in a browser
request. Reserved duplicates must get independent native data, not a shared
folder. Legacy native projects are not silently scanned or deduplicated.
"""
from __future__ import annotations

import fcntl
import hashlib
import os
import re
import sqlite3
import stat
import uuid
from contextlib import closing, contextmanager
from pathlib import Path
from dataclasses import dataclass

from canonical_project_slots import canonical_name
from urano.project_catalog import ProjectCatalog


class SlotConflict(RuntimeError):
    """Revision or canonical title conflict; no data should be overwritten."""


class SlotNotFound(LookupError):
    """Wrong Owner or unknown UUID; do not disclose existence."""


class SlotNotReady(RuntimeError):
    """Reservation/clone not yet backed by its own native project."""


_ID = re.compile(r"[a-f0-9]{64}\Z")


@dataclass(frozen=True)
class ProjectSlot:
    id: str
    kind: str
    title: str
    canonical_title: str
    revision: int
    state: str
    clone_from: str | None
    snapshot_sha256: str | None
    native_ref: str | None
    created_at: str
    updated_at: str


class OwnerProjectSlotRegistry:
    """One canonical (Owner, kind, normalized title) with SQLite writer lock.

    Native projects are only selected through an independent trusted
    filesystem validator before bind; the slot registry is never a public
    filesystem-path oracle or a copy engine.
    """
    def __init__(self, catalog: ProjectCatalog):
        if not isinstance(catalog, ProjectCatalog):
            raise TypeError("Trusted private Owner ProjectCatalog required")
        self.catalog = catalog
        # One private namespace for Save, Rename and Duplicate across processes.
        self.lock_root = Path(catalog.db_path).parent / "canonical-project-writers"
        if self.lock_root.is_symlink():
            raise PermissionError("Project lock directory cannot be a link")
        self.lock_root.mkdir(mode=0o700, exist_ok=True)
        if (self.lock_root.is_symlink() or
                stat.S_IMODE(self.lock_root.stat().st_mode) != 0o700):
            raise PermissionError("Project writer locks require private 0700")
        with closing(catalog._connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS urano_canonical_project_slots(
                slot_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                kind TEXT NOT NULL CHECK(kind IN ('audio','video')),
                title TEXT NOT NULL,
                canonical_title TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 0 CHECK(revision >= 0),
                state TEXT NOT NULL CHECK(state IN ('reserved','bound')),
                clone_from TEXT,
                native_ref TEXT,
                snapshot_sha256 TEXT,
                created_at TEXT NOT NULL DEFAULT
                  (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                updated_at TEXT NOT NULL DEFAULT
                  (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                UNIQUE(owner_id,kind,canonical_title),
                UNIQUE(owner_id,kind,native_ref)
            )""")
            db.execute("""CREATE INDEX IF NOT EXISTS urano_slot_owner
                ON urano_canonical_project_slots(owner_id,kind,updated_at DESC)""")

    @staticmethod
    def _owner(owner_id):
        return ProjectCatalog._principal(owner_id)

    @staticmethod
    def _kind(kind):
        if type(kind) is not str or kind not in ("video","audio"):
            raise ValueError("Unknown project kind")
        return kind

    @staticmethod
    def _title(title):
        key = canonical_name(title)
        # retain formatting but remove only leading/trailing Unicode whitespace
        if len(title.strip()) > 120:
            raise ValueError("Project title too long")
        return " ".join(title.split()), key

    @staticmethod
    def _uuid(project_id):
        return ProjectCatalog._project_id(project_id)

    @staticmethod
    def _revision(expected_revision):
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("Revision must be nonnegative int")
        return expected_revision

    @staticmethod
    def _record(row):
        return ProjectSlot(
            id=row["slot_id"], kind=row["kind"], title=row["title"],
            canonical_title=row["canonical_title"], revision=row["revision"],
            state=row["state"], clone_from=row["clone_from"],
            snapshot_sha256=row["snapshot_sha256"], native_ref=row["native_ref"],
            created_at=row["created_at"], updated_at=row["updated_at"])

    @staticmethod
    def _row(db, owner, project_id):
        row = db.execute("""SELECT * FROM urano_canonical_project_slots
               WHERE owner_id=? AND slot_id=?""",
                         (owner,project_id)).fetchone()
        if row is None:
            raise SlotNotFound("Canonical project unavailable to this Owner")
        return row

    @staticmethod
    def _collision(exc):
        if isinstance(exc,sqlite3.IntegrityError):
            raise SlotConflict(
                "Title or native project already reserved for this Owner/kind"
            ) from exc
        raise exc

    def create(self, *, owner_id, kind, title):
        owner,kind=self._owner(owner_id),self._kind(kind)
        display,key=self._title(title)
        with closing(self.catalog._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            project_id=str(uuid.uuid4())
            try:
                db.execute("""INSERT INTO urano_canonical_project_slots
                   (slot_id,owner_id,kind,title,canonical_title,state)
                   VALUES (?,?,?,?,?,'reserved')""",
                   (project_id,owner,kind,display,key))
            except sqlite3.IntegrityError as exc:
                self._collision(exc)
            return self._record(self._row(db,owner,project_id))

    def get(self, *, owner_id, project_id):
        owner=self._owner(owner_id);project_id=self._uuid(project_id)
        with closing(self.catalog._connect()) as db:
            return self._record(self._row(db,owner,project_id))

    def list_for(self, *, owner_id, kind=None):
        owner=self._owner(owner_id)
        if kind is not None:kind=self._kind(kind)
        with closing(self.catalog._connect()) as db:
            if kind:
                rows=db.execute("""SELECT * FROM urano_canonical_project_slots
                    WHERE owner_id=? AND kind=?
                    ORDER BY updated_at DESC,slot_id ASC""",(owner,kind)).fetchall()
            else:
                rows=db.execute("""SELECT * FROM urano_canonical_project_slots
                    WHERE owner_id=? ORDER BY updated_at DESC,slot_id ASC""",
                    (owner,)).fetchall()
        return [self._record(row) for row in rows]

    def find_by_title(self, *, owner_id, kind, title):
        owner,kind=self._owner(owner_id),self._kind(kind)
        _,key=self._title(title)
        with closing(self.catalog._connect()) as db:
            row=db.execute("""SELECT * FROM urano_canonical_project_slots
                WHERE owner_id=? AND kind=? AND canonical_title=?""",
                (owner,kind,key)).fetchone()
        return self._record(row) if row is not None else None

    def rename(self, *, owner_id, project_id, title, expected_revision):
        with self.native_writer_lock(
                owner_id=owner_id, project_id=project_id,
                lock_root=self.lock_root):
            return self._rename_locked(owner_id=owner_id, project_id=project_id, title=title, expected_revision=expected_revision)

    def _rename_locked(self, *, owner_id, project_id, title, expected_revision):
        """Explicit rename of canonical metadata; Engine name sync separate."""
        owner=self._owner(owner_id);pid=self._uuid(project_id)
        display,key=self._title(title)
        rev=self._revision(expected_revision)
        with closing(self.catalog._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            self._row(db,owner,pid)
            try:
                result=db.execute("""UPDATE urano_canonical_project_slots SET
                    title=?,canonical_title=?,revision=revision+1,
                    updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
                    WHERE owner_id=? AND slot_id=? AND revision=?""",
                    (display,key,owner,pid,rev))
            except sqlite3.IntegrityError as exc:
                self._collision(exc)
            if result.rowcount != 1:
                raise SlotConflict("A newer project revision exists; reload")
            return self._record(self._row(db,owner,pid))

    def duplicate_as_new(self, *, owner_id, project_id, title,
                         expected_revision):
        with self.native_writer_lock(
                owner_id=owner_id, project_id=project_id,
                lock_root=self.lock_root):
            return self._duplicate_locked(owner_id=owner_id, project_id=project_id, title=title, expected_revision=expected_revision)

    def _duplicate_locked(self, *, owner_id, project_id, title,
                         expected_revision):
        """Make an independent UNBOUND identity. Native files never aliased.

        Calling service must create a separate native project snapshot, then
        bind/commit it. Do not show reserved clone as a reopened copy.
        """
        owner=self._owner(owner_id);pid=self._uuid(project_id)
        display,key=self._title(title);rev=self._revision(expected_revision)
        with closing(self.catalog._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            original=self._row(db,owner,pid)
            if original["revision"] != rev:
                raise SlotConflict("Source revision changed before duplication")
            if original["state"] != "bound":
                raise SlotNotReady("Source project not durably bound")
            new_id=str(uuid.uuid4())
            try:
                db.execute("""INSERT INTO urano_canonical_project_slots
                    (slot_id,owner_id,kind,title,canonical_title,state,clone_from)
                    VALUES(?,?,?,?,?,'reserved',?)""",
                    (new_id,owner,original["kind"],display,key,pid))
            except sqlite3.IntegrityError as exc:
                self._collision(exc)
            return self._record(self._row(db,owner,new_id))

    def bind_native_verified(self, *, owner_id, project_id, native_ref,
                             expected_revision, verified=False):
        """Privileged internal API: *caller* must validate project against Owner.

        No raw browser-provided folder must reach this method. This guard
        requires explicit verified=True from a trusted filesystem/storage
        inspector, not from IPC JSON or HTTP.
        """
        if verified is not True:
            raise PermissionError("Native reference must be independently verified")
        if (type(native_ref) is not str or len(native_ref)>1024 or
                not native_ref or "\x00" in native_ref or
                any(ord(c)<32 for c in native_ref)):
            raise ValueError("Invalid verified native reference")
        owner=self._owner(owner_id);pid=self._uuid(project_id)
        rev=self._revision(expected_revision)
        with closing(self.catalog._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row=self._row(db,owner,pid)
            if row["revision"] != rev:
                raise SlotConflict("Project was updated concurrently")
            if row["native_ref"] is not None:
                if row["native_ref"]==native_ref:
                    return self._record(row)
                raise SlotConflict("Immutable native binding already exists")
            try:
                result=db.execute("""UPDATE urano_canonical_project_slots SET
                    native_ref=?,state='bound',revision=revision+1,
                    updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
                    WHERE owner_id=? AND slot_id=? AND revision=?
                    AND native_ref IS NULL AND state='reserved'""",
                    (native_ref,owner,pid,rev))
            except sqlite3.IntegrityError as exc:
                self._collision(exc)
            if result.rowcount!=1:
                raise SlotConflict("Native bind race")
            return self._record(self._row(db,owner,pid))

    @contextmanager
    def native_writer_lock(self, *, owner_id, project_id, lock_root):
        """Exclusive OS lock spanning the native file write AND CAS commit.

        Callers MUST use this whenever a writable native project is touched,
        including new input selection, changes, rename and export metadata.
        Lock directory is a trusted private service-owned directory, not
        provided by the browser. A lock alone does not make unchecked writes
        safe; callers must write atomically and fsync native project files.
        """
        owner=self._owner(owner_id)
        pid=self._uuid(project_id)
        root=Path(lock_root)
        if (root.is_symlink() or not root.is_dir() or
                stat.S_IMODE(root.stat().st_mode) != 0o700):
            raise PermissionError("Private 0700 lock directory required")
        # This lock name reveals no owner; never trust browser path components.
        token=hashlib.sha256(owner.encode("utf-8")+bytes([0])+pid.encode("ascii")).hexdigest()
        filename=root/(token+".lock")
        flags=os.O_RDWR|os.O_CREAT
        if hasattr(os,"O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd=os.open(str(filename),flags,0o600)
        try:
            st=os.fstat(fd)
            if (not stat.S_ISREG(st.st_mode) or
                    stat.S_IMODE(st.st_mode)!=0o600 or
                    st.st_nlink!=1):
                raise PermissionError("Invalid private lock file")
            fcntl.flock(fd,fcntl.LOCK_EX)
            yield
        finally:
            try:fcntl.flock(fd,fcntl.LOCK_UN)
            finally:os.close(fd)

    def save_with_native_writer(self, *, owner_id, project_id,
                                expected_revision, lock_root, writer):
        """The only approved future native-save integration entry point.

        The trusted writer callback executes inside the process-wide file
        lock and MUST save and fsync the native project atomically, then
        return the sha256 digest of the persisted project file. The CAS
        check happens BEFORE touching any bytes. A stale browser revision
        never enters the writer callback. Browser cannot supply writer.
        """
        if not callable(writer):
            raise TypeError("Trusted native persistence callback required")
        if Path(lock_root).resolve() != self.lock_root.resolve():
            raise PermissionError("Save/Rename/Duplicate must share Owner lock namespace")
        with self.native_writer_lock(owner_id=owner_id,
                                     project_id=project_id,lock_root=self.lock_root):
            project=self.get(owner_id=owner_id,project_id=project_id)
            if project.state!="bound":
                raise SlotNotReady("Native project must be ready")
            if project.revision!=self._revision(expected_revision):
                raise SlotConflict("Project changed; reopen latest before saving")
            digest=writer(project)
            if not isinstance(digest,str) or not _ID.fullmatch(digest):
                raise ValueError("Trusted writer did not confirm durable sha256")
            return self.commit_snapshot(
                owner_id=owner_id,project_id=project_id,
                expected_revision=expected_revision,
                native_ref=project.native_ref,snapshot_sha256=digest)

    def commit_snapshot(self, *, owner_id, project_id, expected_revision,
                        native_ref, snapshot_sha256):
        """CAS records a *previously persisted* verified native snapshot digest.

        Digest is not data; API caller must hash+fsync the native project
        independently while its writer lock is held. This does not rewrite
        project files or invent export validation.
        """
        if (type(snapshot_sha256) is not str or
                not _ID.fullmatch(snapshot_sha256)):
            raise ValueError("Invalid snapshot SHA256")
        owner=self._owner(owner_id);pid=self._uuid(project_id)
        rev=self._revision(expected_revision)
        with closing(self.catalog._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row=self._row(db,owner,pid)
            if row["state"]!="bound" or row["native_ref"]!=native_ref:
                raise SlotNotReady("Native project not bound to slot")
            result=db.execute("""UPDATE urano_canonical_project_slots SET
                snapshot_sha256=?,revision=revision+1,
                updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
                WHERE owner_id=? AND slot_id=? AND revision=?""",
                (snapshot_sha256,owner,pid,rev))
            if result.rowcount!=1:
                raise SlotConflict("A newer snapshot exists; reload project")
            return self._record(self._row(db,owner,pid))
