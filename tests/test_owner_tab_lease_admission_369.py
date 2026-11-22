"""Strict authenticated broker IPC for future Owner tab registry (no VM)."""
import json
import tempfile
import unittest
from pathlib import Path

from urano.job_recovery_ledger import JobRecoveryLedger
from urano.owner_tab_lease_admission import verify_tab_operation
from urano.owner_tab_lease_guard import OwnerTabLeaseGuard
from urano.private_broker_service import DemoBroker
from urano.project_catalog import ProjectCatalog
from urano.session_auth import SessionStore


class TabAdmission369(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="montara-369-ipc-")
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.sessions=SessionStore(self.root/"sessions.sqlite3")
        self.catalog=ProjectCatalog(self.root/"projects.sqlite3")
        self.a=self.sessions.issue("owner-a")
        self.b=self.sessions.issue("owner-b")
        self.project_a=self.catalog.create("owner-a","Stage A").id
        self.project_b=self.catalog.create("owner-b","Stage B").id
        self.ledger=JobRecoveryLedger(self.root/"jobs.sqlite3")
        self.job=self.ledger.start_trusted("owner-a",self.project_a)
        self.ledger.reserve_target_unit(self.job)
        self.ledger.mark_running(self.job)

    def frame(self,op="tab_open",session=None,project=None,**kwargs):
        session=session or self.a
        d=dict(op=op,session=session.token,csrf=session.csrf,
               project_id=project or self.project_a,generation=1)
        d.update(kwargs)
        return json.dumps(d,separators=(",",":")).encode()

    def verify(self,packet):
        return verify_tab_operation(packet,owner_db_root=self.root)

    def test_authorized_root_verification_matches_server_owner_and_hash(self):
        result=self.verify(self.frame())
        self.assertEqual((result.operation,result.owner,result.project,result.generation),
                         ("tab_open","owner-a",self.project_a,1))
        self.assertEqual(result.session_hash,
                         OwnerTabLeaseGuard.verified_session_hash(self.a.token))
        self.assertNotEqual(result.session_hash,self.a.token)

    def test_foreign_owner_project_denied(self):
        with self.assertRaises(PermissionError):
            self.verify(self.frame(project=self.project_b))
        with self.assertRaises(PermissionError):
            self.verify(self.frame(session=self.b))

    def test_rotated_csrf_or_revoked_session_denied(self):
        old=self.frame()
        self.sessions.rotate_csrf(self.a.token)
        with self.assertRaises(PermissionError):
            self.verify(old)
        self.sessions.revoke(self.b.token)
        with self.assertRaises(PermissionError):
            self.verify(self.frame(session=self.b,project=self.project_b))

    def test_browser_cannot_submit_idle_proof_or_override_unit_owner(self):
        for extra in ({"owner":"owner-b"},{"pid":1234},
                      {"unit":"montara-h4-job-123"},{"ready":True},
                      {"companion_mp4_ready":True},{"path":"/tmp/anything"}):
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                self.verify(self.frame(**extra))

    def test_broker_frame_operations_are_schema_locked(self):
        tab="a"*48
        op="b"*48
        cases=[
            ("tab_heartbeat",{"lease_id":tab}),
            ("tab_leave",{"lease_id":tab}),
            ("tab_rpc_begin",{"lease_id":tab}),
            ("tab_rpc_finish",{"lease_id":tab,"operation_id":op}),
        ]
        for name,extras in cases:
            with self.subTest(name=name):
                value=self.verify(self.frame(op=name,**extras))
                self.assertEqual(value.operation,name)
                self.assertEqual(value.lease_id,tab)
                self.assertEqual(value.operation_id,op if name=="tab_rpc_finish" else None)

    def test_invalid_tokens_denied(self):
        for value in ("a"*40,"A"*48,"../escape",None,""):
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.verify(self.frame(op="tab_heartbeat",lease_id=value))

    def test_invalid_generation_denied(self):
        for value in (True,0,-1,"1",2**36,None):
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.verify(self.frame(generation=value))

    def test_canonical_project_required(self):
        for value in ("not-a-uuid","../foreign",self.project_a.upper()):
            with self.subTest(project=value),self.assertRaises((ValueError,PermissionError)):
                self.verify(self.frame(project=value))

    def test_root_broker_methods_link_to_actual_sqlite_guard(self):
        b=DemoBroker.__new__(DemoBroker)
        b.ledger=self.ledger
        register=self.verify(self.frame())
        opened=b.verified_owner_tab_action(register)
        self.assertTrue(opened["ok"])
        token=opened["tab_lease"]
        renew=self.verify(self.frame("tab_heartbeat",lease_id=token))
        renewed=b.verified_owner_tab_action(renew)
        self.assertTrue(renewed["ok"])
        started=b.verified_owner_tab_action(
            self.verify(self.frame("tab_rpc_begin",lease_id=token)))
        self.assertTrue(started["ok"])
        result=b.verified_owner_tab_action(self.verify(
            self.frame("tab_rpc_finish",lease_id=token,
                       operation_id=started["operation_id"])))
        self.assertTrue(result["finished"])
        left=b.verified_owner_tab_action(
            self.verify(self.frame("tab_leave",lease_id=token)))
        self.assertTrue(left["released"])
        self.assertEqual(self.ledger.get_trusted(self.job.job_id).state,"running")

    def test_broker_ipc_rejects_foreign_owner_token(self):
        b=DemoBroker.__new__(DemoBroker)
        b.ledger=self.ledger
        token=b.verified_owner_tab_action(self.verify(self.frame()))["tab_lease"]
        with self.assertRaises(PermissionError):
            b.verified_owner_tab_action(self.verify(self.frame(
                "tab_leave",session=self.b,project=self.project_b,lease_id=token)))

    def test_frame_limit(self):
        biggest=self.frame("tab_rpc_finish",lease_id="a"*48,operation_id="b"*48)
        self.assertLessEqual(len(biggest),384)


if __name__=="__main__":
    unittest.main()
