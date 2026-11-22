"""#380 atomic Owner/title/kind registry. Real SQLite, synthetic media only."""
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
import time
import tempfile
import unittest
from pathlib import Path
from threading import Barrier

from urano.project_catalog import ProjectCatalog
from urano.owner_project_slot_registry import (
    OwnerProjectSlotRegistry, SlotConflict, SlotNotFound, SlotNotReady
)


class CanonicalServerSlots380(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="slot380-")
        self.addCleanup(tmp.cleanup)
        self.home=Path(tmp.name)
        self.catalog=ProjectCatalog(self.home/"owner.sqlite3")
        self.registry=OwnerProjectSlotRegistry(self.catalog)

    def create(self,title="Insel Gig",owner="owner-jm",kind="video"):
        return self.registry.create(owner_id=owner,kind=kind,title=title)

    def bind(self,slot,ref=None,owner="owner-jm"):
        return self.registry.bind_native_verified(
            owner_id=owner,project_id=slot.id,native_ref=ref or "/trusted/"+slot.id,
            expected_revision=slot.revision,verified=True)

    def snapshot(self,slot,owner="owner-jm",sha=None):
        return self.registry.commit_snapshot(
            owner_id=owner,project_id=slot.id,
            native_ref=slot.native_ref,expected_revision=slot.revision,
            snapshot_sha256=sha or hashlib.sha256(b"synthetic snapshot").hexdigest())

    def test_one_title_one_slot_after_casefold_unicode_and_whitespace(self):
        one=self.create("  Ｃａｆｅ́  Concert  ")
        self.assertEqual(one.canonical_title,"café concert")
        for title in ("CAFÉ  concert","cafe\u0301 concert","ｃａｆé concert"):
            with self.subTest(title=title),self.assertRaises(SlotConflict):
                self.create(title)
        self.assertEqual(len(self.registry.list_for(owner_id="owner-jm")),1)

    def test_audio_and_video_same_title_belong_to_distinct_slots(self):
        video=self.create("Live",kind="video")
        audio=self.create("live",kind="audio")
        self.assertNotEqual(video.id,audio.id)
        self.assertEqual(len(self.registry.list_for(owner_id="owner-jm")),2)
        self.assertEqual(len(self.registry.list_for(owner_id="owner-jm",kind="audio")),1)

    def test_different_owners_can_use_same_title_without_visibility(self):
        first=self.create("Live")
        second=self.create("Live",owner="owner-fer")
        self.assertNotEqual(first.id,second.id)
        self.assertEqual(len(self.registry.list_for(owner_id="owner-fer")),1)
        with self.assertRaises(SlotNotFound):
            self.registry.get(owner_id="owner-fer",project_id=first.id)
        with self.assertRaises(SlotNotFound):
            self.registry.rename(owner_id="owner-fer",project_id=first.id,
                                 expected_revision=0,title="stolen")

    def test_concurrent_create_exactly_one_success(self):
        barrier=Barrier(8)
        def create(i):
            registry=OwnerProjectSlotRegistry(ProjectCatalog(self.catalog.db_path))
            barrier.wait()
            try:return ("created",registry.create(
                owner_id="owner-jm",kind="video",title="Dupe   Name" if i%2 else "dupe name").id)
            except SlotConflict:return ("conflict",None)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results=list(executor.map(create,range(8)))
        self.assertEqual([x[0] for x in results].count("created"),1)
        self.assertEqual([x[0] for x in results].count("conflict"),7)
        self.assertEqual(len(self.registry.list_for(owner_id="owner-jm")),1)

    def test_reconnect_new_registry_preserves_identity_revision(self):
        row=self.create()
        row=self.bind(row)
        row=self.snapshot(row)
        restarted=OwnerProjectSlotRegistry(ProjectCatalog(self.catalog.db_path))
        same=restarted.find_by_title(owner_id="owner-jm",kind="video",title="insel GIG")
        self.assertEqual((same.id,same.revision,same.snapshot_sha256),
                         (row.id,row.revision,row.snapshot_sha256))

    def test_bind_needs_trusted_ownership_check(self):
        row=self.create()
        with self.assertRaises(PermissionError):
            self.registry.bind_native_verified(
                owner_id="owner-jm",project_id=row.id,native_ref="/owner/jm/project",
                expected_revision=0,verified=False)
        self.assertEqual(self.registry.get(owner_id="owner-jm",project_id=row.id).state,"reserved")

    def test_one_native_reference_cannot_back_two_slots(self):
        a=self.create("One")
        b=self.create("Two")
        self.bind(a,ref="/trusted/one")
        with self.assertRaises(SlotConflict):
            self.bind(b,ref="/trusted/one")
        self.assertEqual(self.registry.get(owner_id="owner-jm",project_id=b.id).state,"reserved")

    def test_native_binding_is_immutable_no_arbitrary_retarget(self):
        row=self.bind(self.create(),ref="/trusted/a")
        same=self.registry.bind_native_verified(
            owner_id="owner-jm",project_id=row.id,native_ref="/trusted/a",
            expected_revision=row.revision,verified=True)
        self.assertEqual(same.id,row.id)
        with self.assertRaises(SlotConflict):
            self.registry.bind_native_verified(
                owner_id="owner-jm",project_id=row.id,native_ref="/trusted/b",
                expected_revision=row.revision,verified=True)
        self.assertEqual(self.registry.get(owner_id="owner-jm",project_id=row.id).native_ref,"/trusted/a")

    def test_stale_save_does_not_overwrite_latest_snapshot(self):
        row=self.bind(self.create())
        first=self.snapshot(row,sha="1"*64)
        with self.assertRaises(SlotConflict):
            self.snapshot(row,sha="2"*64)
        current=self.registry.get(owner_id="owner-jm",project_id=row.id)
        self.assertEqual((current.snapshot_sha256,current.revision),("1"*64,first.revision))

    def test_two_simultaneous_saves_one_wins(self):
        row=self.bind(self.create())
        barrier=Barrier(2)
        def write(i):
            db=OwnerProjectSlotRegistry(ProjectCatalog(self.catalog.db_path))
            barrier.wait()
            try:
                result=db.commit_snapshot(
                    owner_id="owner-jm",project_id=row.id,
                    native_ref=row.native_ref,expected_revision=row.revision,
                    snapshot_sha256=str(i)*64)
                return ("saved",result.snapshot_sha256)
            except SlotConflict:return ("conflict",None)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            results=list(ex.map(write,(1,2)))
        self.assertCountEqual([r[0] for r in results],["saved","conflict"])
        self.assertEqual(self.registry.get(owner_id="owner-jm",project_id=row.id).revision,row.revision+1)

    def test_reserved_project_cannot_be_saved_or_duplicated(self):
        row=self.create()
        with self.assertRaises(SlotNotReady):
            self.registry.commit_snapshot(owner_id="owner-jm",project_id=row.id,
                native_ref="/something",expected_revision=0,snapshot_sha256="a"*64)
        with self.assertRaises(SlotNotReady):
            self.registry.duplicate_as_new(owner_id="owner-jm",project_id=row.id,
                                           title="Another",expected_revision=0)

    def test_explicit_rename_with_cas_keeps_same_uuid(self):
        row=self.bind(self.create("Old"))
        renamed=self.registry.rename(owner_id="owner-jm",project_id=row.id,
                                     title="New Title",expected_revision=row.revision)
        self.assertEqual(row.id,renamed.id)
        self.assertEqual(renamed.native_ref,row.native_ref)
        self.assertEqual(renamed.revision,row.revision+1)
        self.assertIsNone(self.registry.find_by_title(owner_id="owner-jm",kind="video",title="Old"))
        with self.assertRaises(SlotConflict):
            self.registry.rename(owner_id="owner-jm",project_id=row.id,
                                 title="Old",expected_revision=row.revision)

    def test_rename_to_occupied_title_is_rejected(self):
        first=self.create("One")
        other=self.create("Other")
        with self.assertRaises(SlotConflict):
            self.registry.rename(owner_id="owner-jm",project_id=other.id,
                                 title="  ONE  ",expected_revision=other.revision)
        self.assertEqual(self.registry.get(owner_id="owner-jm",project_id=other.id).title,"Other")

    def test_explicit_duplicate_has_distinct_uuid_and_no_aliasing(self):
        row=self.bind(self.create("Song"))
        row=self.snapshot(row)
        duplicate=self.registry.duplicate_as_new(
            owner_id="owner-jm",project_id=row.id,title="Song - Copy",
            expected_revision=row.revision)
        self.assertNotEqual(duplicate.id,row.id)
        self.assertEqual(duplicate.clone_from,row.id)
        self.assertEqual(duplicate.state,"reserved")
        self.assertIsNone(duplicate.native_ref)
        self.assertIsNone(duplicate.snapshot_sha256)
        fresh=self.bind(duplicate,ref="/trusted/fresh-project")
        self.assertNotEqual(fresh.native_ref,row.native_ref)
        self.assertEqual(self.registry.get(owner_id="owner-jm",project_id=row.id).snapshot_sha256,
                         row.snapshot_sha256)

    def test_duplicate_must_not_replace_existing_title_or_wrong_revision(self):
        row=self.bind(self.create("Source"))
        self.create("Copy")
        with self.assertRaises(SlotConflict):
            self.registry.duplicate_as_new(owner_id="owner-jm",project_id=row.id,
                                           title="COPY",expected_revision=row.revision)
        with self.assertRaises(SlotConflict):
            self.registry.duplicate_as_new(owner_id="owner-jm",project_id=row.id,
                                           title="Copy 2",expected_revision=row.revision+1)
        self.assertEqual(len(self.registry.list_for(owner_id="owner-jm")),2)

    def test_missing_owner_and_invalid_ids_fail_closed(self):
        row=self.create()
        for key in ("../escape","",str(row.id).upper(),None):
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.registry.get(owner_id="owner-jm",project_id=key)
        with self.assertRaises(SlotNotFound):
            self.registry.get(owner_id="owner-fer",project_id=row.id)

    def test_reject_invalid_kind_title_and_hash(self):
        for value in ("pictures","",None):
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.create(kind=value)
        for value in ("", "X"*121, "bad\x00title"):
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.create(title=value)
        row=self.bind(self.create())
        with self.assertRaises(ValueError):
            self.snapshot(row,sha="../bad")

    def test_atomic_native_writer_blocks_stale_save_before_touching_media(self):
        row=self.bind(self.create())
        lock_root=self.home/"locks"
        lock_root.mkdir(mode=0o700)
        real=self.home/"native-project.json"
        real.write_text('{"revision":"original"}')
        entered=[]
        barrier=Barrier(2)

        def save(value):
            registry=OwnerProjectSlotRegistry(ProjectCatalog(self.catalog.db_path))
            barrier.wait()
            def writer(current):
                entered.append(value)
                temp=real.with_name(real.name+"."+value)
                data=('{"revision":"'+value+'"}').encode()
                with temp.open("wb") as out:
                    out.write(data)
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(temp,real)
                return hashlib.sha256(real.read_bytes()).hexdigest()
            try:
                return ("saved", registry.save_with_native_writer(
                    owner_id="owner-jm",project_id=row.id,
                    expected_revision=row.revision,lock_root=self.registry.lock_root,
                    writer=writer))
            except SlotConflict:
                return ("conflict",None)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            results=list(ex.map(save,("one","two")))
        self.assertCountEqual([x[0] for x in results],["saved","conflict"])
        self.assertEqual(len(entered),1,"Stale writer callback must never run")
        expected=hashlib.sha256(real.read_bytes()).hexdigest()
        self.assertEqual(self.registry.get(owner_id="owner-jm",
                                            project_id=row.id).snapshot_sha256,expected)

    def test_native_writer_lock_rejects_untrusted_directory_or_symlink(self):
        row=self.bind(self.create())
        public=self.home/"public"
        public.mkdir(mode=0o755)
        called=[]
        for path in (public,self.home/"missing"):
            with self.subTest(path=path),self.assertRaises(PermissionError):
                self.registry.save_with_native_writer(
                    owner_id="owner-jm",project_id=row.id,
                    expected_revision=row.revision,lock_root=path,
                    writer=lambda p:called.append(True))
        linked=self.home/"linked"
        linked.symlink_to(public)
        with self.assertRaises(PermissionError):
            self.registry.save_with_native_writer(
                owner_id="owner-jm",project_id=row.id,
                expected_revision=row.revision,lock_root=linked,
                writer=lambda p:called.append(True))
        self.assertEqual(called,[])

    def test_native_writer_exception_preserves_registry_revision(self):
        row=self.bind(self.create())
        root=self.home/"locks";root.mkdir(mode=0o700)
        def failure(project):
            raise OSError("synthetic disk full")
        with self.assertRaises(OSError):
            self.registry.save_with_native_writer(
                owner_id="owner-jm",project_id=row.id,
                expected_revision=row.revision,lock_root=self.registry.lock_root,
                writer=failure)
        self.assertEqual(self.registry.get(owner_id="owner-jm",
                                           project_id=row.id).revision,row.revision)

    def test_save_vs_rename_never_overwrites_native_file_after_stale_cas(self):
        row=self.bind(self.create())
        media=self.home/"project.json"
        media.write_bytes(b"original")
        barrier=Barrier(2)
        calls=[]
        def save():
            registry=OwnerProjectSlotRegistry(ProjectCatalog(self.catalog.db_path))
            barrier.wait()
            def writer(project):
                calls.append("wrote")
                media.write_bytes(b"saved")
                return hashlib.sha256(media.read_bytes()).hexdigest()
            try:
                registry.save_with_native_writer(
                    owner_id="owner-jm",project_id=row.id,
                    expected_revision=row.revision,lock_root=registry.lock_root,
                    writer=writer)
                return "saved"
            except SlotConflict:
                return "conflict"
        def rename():
            registry=OwnerProjectSlotRegistry(ProjectCatalog(self.catalog.db_path))
            barrier.wait()
            try:
                registry.rename(owner_id="owner-jm",project_id=row.id,
                                title="New title",expected_revision=row.revision)
                return "renamed"
            except SlotConflict:
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=[pool.submit(save),pool.submit(rename)]
            outcomes=sorted(f.result() for f in results)
        self.assertIn(outcomes,[["conflict","renamed"],["conflict","saved"]])
        if "renamed" in outcomes:
            self.assertEqual(media.read_bytes(),b"original")
            self.assertEqual(calls,[])
        else:
            self.assertEqual(media.read_bytes(),b"saved")
            self.assertEqual(calls,["wrote"])

    def test_save_vs_duplicate_reserves_after_consistent_source_revision(self):
        row=self.bind(self.create())
        barrier=Barrier(2)
        def save():
            reg=OwnerProjectSlotRegistry(ProjectCatalog(self.catalog.db_path))
            barrier.wait()
            try:
                reg.save_with_native_writer(
                    owner_id="owner-jm",project_id=row.id,
                    expected_revision=row.revision,lock_root=reg.lock_root,
                    writer=lambda _: "f"*64)
                return "saved"
            except SlotConflict:return "conflict"
        def duplicate():
            reg=OwnerProjectSlotRegistry(ProjectCatalog(self.catalog.db_path))
            barrier.wait()
            try:
                copy=reg.duplicate_as_new(
                    owner_id="owner-jm",project_id=row.id,title="New Copy",
                    expected_revision=row.revision)
                self.assertIsNone(copy.native_ref)
                return "duplicated"
            except SlotConflict:return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            fs=[pool.submit(save),pool.submit(duplicate)]
            outcomes=sorted(f.result() for f in fs)
        # A clone may finish under the lock, followed by a legitimate Save.
        # Both then succeed in a valid serialized order; stale clones fail
        # only when the native source Save acquired the lock first.
        self.assertIn(outcomes,[["conflict","saved"],["duplicated","saved"]])

    def test_rename_and_duplicate_need_refresh_after_concurrent_save(self):
        row=self.bind(self.create("A title"))
        root=self.home/"locks";root.mkdir(mode=0o700)
        current=self.registry.save_with_native_writer(
            owner_id="owner-jm",project_id=row.id,
            expected_revision=row.revision,lock_root=self.registry.lock_root,
            writer=lambda p:"a"*64)
        with self.assertRaises(SlotConflict):
            self.registry.rename(owner_id="owner-jm",project_id=row.id,
                                 title="Other",expected_revision=row.revision)
        with self.assertRaises(SlotConflict):
            self.registry.duplicate_as_new(owner_id="owner-jm",
                project_id=row.id,title="Other copy",
                expected_revision=row.revision)
        self.assertEqual(self.registry.get(owner_id="owner-jm",
                                           project_id=row.id).revision,current.revision)

    def test_no_native_project_copied_or_overwritten_by_registry(self):
        marker=self.home/"real-existing-project.zuckervid"
        marker.mkdir()
        content=marker/"project.json"
        content.write_text('{"old_video":"original untouched"}')
        old=content.read_bytes()
        a=self.bind(self.create(),ref=str(marker))
        self.snapshot(a)
        self.registry.rename(owner_id="owner-jm",project_id=a.id,
                             title="Updated Display",expected_revision=2)
        self.assertEqual(content.read_bytes(),old)
        self.assertTrue(marker.is_dir())


if __name__=="__main__":
    unittest.main()
