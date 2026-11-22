"""#369 isolated Owner tab/operation acceptance with real SQLite + no systemd."""
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from urano.job_recovery_ledger import JobRecoveryLedger, BusyOwner, StaleJob
from urano.owner_tab_lease_guard import (
    OwnerTabLeaseGuard, TabLeaseDenied, EngineStillBusy, TrustedEngineIdle,
)


class OwnerTabLease369(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="montara-369-")
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.ledger=JobRecoveryLedger(self.root/"jobs.sqlite3")
        self.a=self.ledger.start_trusted("owner-a","project-a")
        self.b=self.ledger.start_trusted("owner-b","project-b")
        for job in (self.a,self.b):
            self.ledger.reserve_target_unit(job)
            self.ledger.mark_running(job)
        self.guard=OwnerTabLeaseGuard(self.ledger,ttl_seconds=90,grace_seconds=120)
        self.now=2000000000
        self.seshash=self.guard.verified_session_hash("a"*64)
        self.seshash2=self.guard.verified_session_hash("b"*64)

    def kwargs(self,job=None,hash=None):
        j=job or self.a
        return dict(owner=j.owner_id,project=j.project_id,
                    generation=j.generation,
                    session_hash=hash or self.seshash)

    def open(self,job=None,hash=None,now=None):
        return self.guard.open_tab(**self.kwargs(job,hash),now=self.now if now is None else now)

    def attestation(self,job=None,**values):
        j=job or self.a
        d=dict(owner_id=j.owner_id,project_id=j.project_id,
               generation=j.generation,local_mp4_verified=True,
               engine_tasks_idle=True,companion_render_idle=True,
               mixer_export_idle=True)
        d.update(values)
        return TrustedEngineIdle(**d)

    def reserve(self,job=None,probe=None,now=None):
        j=job or self.a
        return self.guard.reserve_stop_after_verified_completion(
            owner=j.owner_id,project=j.project_id,generation=j.generation,
            trusted_probe=probe,now=self.now if now is None else now)

    def test_two_tabs_same_owner_second_stays_active_preventing_shutdown(self):
        tab1=self.open()
        tab2=self.open()
        self.guard.leave_tab(lease_id=tab1,**self.kwargs(),now=self.now+3)
        self.assertEqual(self.guard.snapshot(owner="owner-a",project="project-a",generation=1,now=self.now+3).active_tabs,1)
        with self.assertRaises(EngineStillBusy):
            self.reserve(probe=lambda job:self.attestation())
        self.assertEqual(self.ledger.get_trusted(self.a.job_id).state,"running")
        self.assertEqual(self.ledger.get_trusted(self.b.job_id).state,"running")

    def test_both_tabs_released_and_trusted_ready_allows_exact_one_stop_reservation(self):
        tabs=[self.open(),self.open()]
        for tab in tabs:
            self.guard.leave_tab(lease_id=tab,**self.kwargs(),now=self.now+10)
        lease=self.reserve(probe=lambda job:self.attestation(),now=self.now+11)
        self.assertEqual(lease.state,"stopping")
        self.assertEqual(self.ledger.get_trusted(self.a.job_id).state,"stopping")
        self.assertEqual(self.ledger.get_trusted(self.b.job_id).state,"running")
        with self.assertRaises(TabLeaseDenied):
            self.open(now=self.now+12)
        with self.assertRaises((TabLeaseDenied,EngineStillBusy)):
            self.reserve(probe=lambda job:self.attestation(),now=self.now+12)

    def test_no_evidence_always_refuses_even_after_tab_release(self):
        t=self.open()
        self.guard.leave_tab(lease_id=t,**self.kwargs(),now=self.now+1)
        with self.assertRaises(EngineStillBusy):
            self.reserve()
        self.assertEqual(self.ledger.get_trusted(self.a.job_id).state,"running")

    def test_browser_claims_cannot_substitute_for_trusted_completion(self):
        t=self.open()
        self.guard.leave_tab(lease_id=t,**self.kwargs())
        for proof in ("ready", {"videoStatus":"ready"}, None,
                      lambda j: {"ready":True}, lambda j:"ready",
                      lambda j:self.attestation(local_mp4_verified=False),
                      lambda j:self.attestation(companion_render_idle=False),
                      lambda j:self.attestation(engine_tasks_idle=False),
                      lambda j:self.attestation(mixer_export_idle=False)):
            with self.subTest(proof=str(proof)[:35]),self.assertRaises(EngineStillBusy):
                self.reserve(probe=proof)
        self.assertEqual(self.ledger.get_trusted(self.a.job_id).state,"running")

    def test_other_owner_active_is_never_stopped_by_owner_a_shutdown(self):
        tab=self.open()
        other=self.open(job=self.b)
        self.guard.leave_tab(lease_id=tab,**self.kwargs())
        self.reserve(probe=lambda j:self.attestation())
        status=self.guard.snapshot(owner="owner-b",project="project-b",generation=1,now=self.now)
        self.assertEqual(status.active_tabs,1)
        self.assertEqual(self.ledger.get_trusted(self.b.job_id).state,"running")
        self.guard.heartbeat(lease_id=other,**self.kwargs(self.b),now=self.now+2)

    def test_active_rpc_blocks_close_even_when_tab_expired_or_released(self):
        t=self.open()
        op=self.guard.start_rpc(lease_id=t,**self.kwargs(),now=self.now+5)
        self.guard.leave_tab(lease_id=t,**self.kwargs(),now=self.now+8)
        at=self.now+1000
        self.assertEqual(self.guard.snapshot(owner="owner-a",project="project-a",generation=1,now=at).in_flight_operations,1)
        with self.assertRaises(EngineStillBusy):
            self.reserve(probe=lambda j:self.attestation(),now=at)
        self.assertTrue(self.guard.finish_rpc(operation_id=op,lease_id=t,**self.kwargs()))
        self.assertFalse(self.guard.finish_rpc(operation_id=op,lease_id=t,**self.kwargs()))
        self.assertEqual(self.reserve(probe=lambda j:self.attestation(),now=at).state,"stopping")

    def test_heartbeat_keeps_tab_alive_through_grace(self):
        t=self.open()
        exp=self.guard.heartbeat(lease_id=t,**self.kwargs(),now=self.now+75)
        self.assertEqual(exp,self.now+165)
        with self.assertRaises(EngineStillBusy):
            self.reserve(probe=lambda j:self.attestation(),now=self.now+250)
        self.assertEqual(self.ledger.get_trusted(self.a.job_id).state,"running")

    def test_abrupt_disconnect_waits_for_ttl_and_grace_then_needs_trusted_proof(self):
        self.open()
        for offset in (1,89,90,91,209):
            with self.assertRaises(EngineStillBusy):
                self.reserve(probe=lambda j:self.attestation(),now=self.now+offset)
        with self.assertRaises(EngineStillBusy):
            self.reserve(now=self.now+211)
        self.assertEqual(self.ledger.get_trusted(self.a.job_id).state,"running")
        self.assertEqual(self.reserve(probe=lambda j:self.attestation(),now=self.now+211).state,"stopping")

    def test_expired_tab_cannot_renew_but_can_reopen_with_new_token(self):
        old=self.open()
        with self.assertRaises(TabLeaseDenied):
            self.guard.heartbeat(lease_id=old,**self.kwargs(),now=self.now+91)
        t2=self.open(now=self.now+91)
        self.assertNotEqual(old,t2)
        self.assertEqual(self.guard.snapshot(owner="owner-a",project="project-a",generation=1,now=self.now+92).active_tabs,2)

    def test_foreign_owner_or_session_cannot_renew_or_release_other_tab(self):
        t=self.open()
        for args in (self.kwargs(self.b), self.kwargs(hash=self.seshash2)):
            with self.subTest(args=args),self.assertRaises(TabLeaseDenied):
                self.guard.heartbeat(lease_id=t,**args,now=self.now+1)
            with self.assertRaises(TabLeaseDenied):
                self.guard.leave_tab(lease_id=t,**args,now=self.now+1)
        self.assertEqual(self.guard.snapshot(owner="owner-a",project="project-a",generation=1,now=self.now+1).active_tabs,1)

    def test_foreign_session_cannot_finish_another_tab_rpc(self):
        t=self.open()
        op=self.guard.start_rpc(lease_id=t,**self.kwargs())
        with self.assertRaises(TabLeaseDenied):
            self.guard.finish_rpc(operation_id=op,lease_id=t,**self.kwargs(hash=self.seshash2))
        other=self.open(hash=self.seshash2)
        with self.assertRaises(TabLeaseDenied):
            self.guard.finish_rpc(operation_id=op,lease_id=other,**self.kwargs(hash=self.seshash2))
        self.assertTrue(self.guard.finish_rpc(operation_id=op,lease_id=t,**self.kwargs()))

    def test_tab_release_idempotent(self):
        t=self.open()
        self.assertTrue(self.guard.leave_tab(lease_id=t,**self.kwargs()))
        self.assertFalse(self.guard.leave_tab(lease_id=t,**self.kwargs()))
        with self.assertRaises(TabLeaseDenied):
            self.guard.start_rpc(lease_id=t,**self.kwargs())
        with self.assertRaises(TabLeaseDenied):
            self.guard.heartbeat(lease_id=t,**self.kwargs())

    def test_stale_generation_denied_after_verified_old_job_stop(self):
        tab=self.open()
        st=self.ledger.request_stop(self.a)
        self.ledger.confirm_stopped(st,verified_cgroup_empty=True)
        new=self.ledger.start_trusted("owner-a","project-a")
        self.ledger.reserve_target_unit(new)
        self.ledger.mark_running(new)
        self.assertEqual(new.generation,2)
        with self.assertRaises(TabLeaseDenied):
            self.guard.heartbeat(lease_id=tab,**self.kwargs())
        with self.assertRaises(TabLeaseDenied):
            self.open()
        tab2=self.open(job=new)
        self.assertTrue(tab2)

    def test_no_known_tab_disallows_auto_stop_of_legacy_shared_engine(self):
        with self.assertRaises(EngineStillBusy):
            self.reserve(probe=lambda j:self.attestation())
        self.assertEqual(self.ledger.get_trusted(self.a.job_id).state,"running")

    def test_cannot_start_more_than_16_active_tabs(self):
        for i in range(16): self.open()
        with self.assertRaises(TabLeaseDenied):
            self.open()
        self.assertEqual(self.guard.snapshot(owner="owner-a",project="project-a",generation=1,now=self.now).active_tabs,16)

    def test_restart_keeps_ledger_and_operation_fences(self):
        t=self.open()
        op=self.guard.start_rpc(lease_id=t,**self.kwargs())
        restarted=OwnerTabLeaseGuard(JobRecoveryLedger(self.ledger.db_path),ttl_seconds=90,grace_seconds=120)
        s=restarted.snapshot(owner="owner-a",project="project-a",generation=1,now=self.now+1000)
        self.assertEqual((s.active_tabs,s.in_flight_operations),(0,1))
        with self.assertRaises(EngineStillBusy):
            restarted.reserve_stop_after_verified_completion(
                owner="owner-a",project="project-a",generation=1,
                trusted_probe=lambda j:self.attestation(),now=self.now+1000)
        self.guard.finish_rpc(operation_id=op,lease_id=t,**self.kwargs())
        self.assertEqual(restarted.reserve_stop_after_verified_completion(
            owner="owner-a",project="project-a",generation=1,
            trusted_probe=lambda j:self.attestation(),now=self.now+1000).state,"stopping")

    def test_concurrent_registration_and_stop_are_atomic(self):
        tab=self.open()
        self.guard.leave_tab(lease_id=tab,**self.kwargs())
        registry2=OwnerTabLeaseGuard(JobRecoveryLedger(self.ledger.db_path),ttl_seconds=90,grace_seconds=120)
        barrier=Barrier(2)
        def stop():
            barrier.wait()
            try:
                self.reserve(probe=lambda j:self.attestation(),now=self.now+1)
                return "stopped"
            except (TabLeaseDenied,EngineStillBusy):
                return "busy"
        def register():
            barrier.wait()
            try:
                registry2.open_tab(**self.kwargs(),now=self.now+1)
                return "opened"
            except TabLeaseDenied:
                return "denied"
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(stop);b=pool.submit(register)
            outcome={a.result(),b.result()}
        self.assertIn(outcome,({"stopped","denied"},{"busy","opened"}))
        if "opened" in outcome:
            self.assertEqual(self.ledger.get_trusted(self.a.job_id).state,"running")
        else:
            self.assertEqual(self.ledger.get_trusted(self.a.job_id).state,"stopping")

    def test_second_stop_reservation_fails_once_reserved(self):
        t=self.open()
        self.guard.leave_tab(lease_id=t,**self.kwargs())
        self.reserve(probe=lambda j:self.attestation())
        with self.assertRaises((TabLeaseDenied,EngineStillBusy)):
            self.reserve(probe=lambda j:self.attestation())

    def test_wrong_type_or_generation_rejected(self):
        for generation in (True,0,-1,2**32,"1",None):
            with self.subTest(generation=generation),self.assertRaises(TabLeaseDenied):
                self.guard.open_tab(owner="owner-a",project="project-a",
                                    generation=generation,session_hash=self.seshash)
        for token in ("../escape","",None,"a"*64):
            with self.subTest(token=token),self.assertRaises(TabLeaseDenied):
                self.guard.heartbeat(lease_id=token,**self.kwargs())

    def test_metadata_does_not_include_session_plaintext(self):
        t=self.open()
        with sqlite3.connect(self.ledger.db_path) as db:
            stored=db.execute("SELECT session_hash FROM urano_owner_tabs WHERE lease_id=?",(t,)).fetchone()[0]
        self.assertEqual(stored,self.seshash)
        self.assertNotEqual(stored,"a"*64)


if __name__=="__main__":
    unittest.main()
