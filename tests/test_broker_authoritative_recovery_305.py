"""#305: a helper/second broker must never kill a live different Owner.

Real SQLite ledger + mocked kernel/systemd; no VM operations.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from urano.broker_daemon_guard import (
    BrokerAlreadyActive, exclusive_broker_daemon, refuse_live_broker_socket,
)
from urano.h4_instance import H4Instance
from urano.job_recovery_ledger import JobRecoveryLedger
from urano.private_broker_service import DemoBroker
from urano.restricted_systemd_broker import RestrictedTargetControl, UnverifiedTarget, expected_cgroup


def missing():
    return {"LoadState":"not-found", "ActiveState":"inactive",
            "SubState":"dead", "MainPID":"0", "ControlGroup":""}


def live(unit):
    return {"LoadState":"loaded","ActiveState":"active","SubState":"running",
            "MainPID":"62000","ControlGroup":expected_cgroup(unit)}


class BrokerRecovery305(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="montara-broker-305-")
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name).resolve()
        self.instance=H4Instance()
        self.ledger_path=self.root/"jobs.sqlite3"
        self.ledger=JobRecoveryLedger(self.ledger_path,instance=self.instance)
        self.first=self.ledger.start_trusted("owner-one","project-one")
        self.second=self.ledger.start_trusted("owner-two","project-two")
        self.aunit=self.ledger.reserve_target_unit(self.first)
        self.bunit=self.ledger.reserve_target_unit(self.second)
        self.ledger.mark_running(self.first)
        self.ledger.mark_running(self.second)
        self.systemd=Mock()

    def make_broker(self):
        # Use real constructor but forbid kernel/systemd commands.
        with patch("urano.private_broker_service.trusted_operator_worker_script",
                   return_value="/operator-pinned-worker"), patch(
                "urano.private_broker_service.SystemdDirect",
                return_value=self.systemd):
            broker=DemoBroker("/opt/montara/bundles/engine-"+"a"*40,
                              ledger_path=self.ledger_path,instance=self.instance)
        return broker

    def assert_both_running(self):
        ledger=JobRecoveryLedger(self.ledger_path,instance=self.instance)
        self.assertEqual(ledger.get_trusted(self.first.job_id).state,"running")
        self.assertEqual(ledger.get_trusted(self.second.job_id).state,"running")

    def test_independent_helper_constructor_does_not_write_ledger_or_stop_anyone(self):
        with patch.object(JobRecoveryLedger,"recover_after_restart",
                          side_effect=AssertionError("Legacy sweep called")):
            helper=self.make_broker()
        self.assertIsNotNone(helper.control)
        self.assert_both_running()
        self.systemd.show.assert_not_called()
        self.systemd.stop_exact.assert_not_called()

    def test_two_live_owner_jobs_remain_running_on_authoritative_restart(self):
        self.systemd.show.side_effect=live
        broker=self.make_broker()
        with patch("urano.restricted_systemd_broker.CGROUP_ROOT",self.root/"cg"):
            outcome=broker.reconcile_on_authoritative_start()
        self.assertEqual(outcome,{"preserved":2,"released_absent":0,"uncertain":0})
        self.assert_both_running()
        self.systemd.stop_exact.assert_not_called()

    def test_restarted_daemon_can_reuse_other_owner_verified_live_worker(self):
        self.systemd.show.side_effect=live
        broker=self.make_broker()
        with patch("urano.restricted_systemd_broker.CGROUP_ROOT",self.root/"cg"):
            broker.reconcile_on_authoritative_start()
        ready_marker='{"ready":true,"uid":30000,"folder":"project-two"}'
        with patch("urano.private_broker_service.Path.read_text",
                   return_value=ready_marker):
            result=broker.ensure_owner("owner-two","project-two")
        self.assertEqual(result["state"],"ready")
        self.assertEqual(result["generation"],self.second.generation)
        self.assert_both_running()
        self.systemd.stop_exact.assert_not_called()

    def test_one_gone_job_released_only_after_double_absence_other_stays_alive(self):
        self.systemd.show.side_effect=lambda unit: missing() if unit==self.aunit else live(unit)
        broker=self.make_broker()
        with patch("urano.restricted_systemd_broker.CGROUP_ROOT",self.root/"cg"):
            outcome=broker.reconcile_on_authoritative_start()
        self.assertEqual(outcome,{"preserved":1,"released_absent":1,"uncertain":0})
        self.assertEqual(self.ledger.get_trusted(self.first.job_id).state,"stopped")
        self.assertEqual(self.ledger.get_trusted(self.second.job_id).state,"running")
        seen=[c.args[0] for c in self.systemd.show.call_args_list]
        self.assertEqual(seen.count(self.aunit),2)
        self.systemd.stop_exact.assert_not_called()

    def test_unknown_kernel_state_fail_closed_does_not_stop_or_reclassify(self):
        self.systemd.show.side_effect=lambda unit: (
            {**missing(),"MainPID":"1"} if unit==self.aunit else live(unit))
        broker=self.make_broker()
        with patch("urano.restricted_systemd_broker.CGROUP_ROOT",self.root/"cg"):
            outcome=broker.reconcile_on_authoritative_start()
        self.assertEqual(outcome,{"preserved":1,"released_absent":0,"uncertain":1})
        self.assert_both_running()
        self.systemd.stop_exact.assert_not_called()

    def test_reappearing_cgroup_refuses_release(self):
        self.systemd.show.side_effect=lambda unit: missing() if unit==self.aunit else live(unit)
        base=self.root/"cg"
        self.cgroup=base/"system.slice"/(self.aunit+".service")
        self.cgroup.mkdir(parents=True)
        broker=self.make_broker()
        with patch("urano.restricted_systemd_broker.CGROUP_ROOT",base):
            outcome=broker.reconcile_on_authoritative_start()
        self.assertEqual(outcome,{"preserved":1,"released_absent":0,"uncertain":1})
        self.assert_both_running()
        self.systemd.stop_exact.assert_not_called()

    def test_no_reserved_unit_remains_fenced(self):
        openlease=self.ledger.start_trusted("owner-three","project-three")
        broker=self.make_broker()
        self.systemd.show.side_effect=live
        with patch("urano.restricted_systemd_broker.CGROUP_ROOT",self.root/"cg"):
            outcome=broker.reconcile_on_authoritative_start()
        self.assertEqual(outcome,{"preserved":2,"released_absent":0,"uncertain":1})
        self.assertEqual(self.ledger.get_trusted(openlease.job_id).state,"starting")
        self.systemd.stop_exact.assert_not_called()

    def test_concurrent_ledger_generation_state_change_blocks_stale_release(self):
        self.systemd.show.side_effect=lambda unit: missing() if unit==self.aunit else live(unit)
        broker=self.make_broker()
        original=broker.control.prove_absent
        def race(lease):
            result=original(lease)
            if lease.job_id==self.first.job_id:
                self.ledger._transition(lease,("running",),"orphaned")
            return result
        with patch.object(broker.control,"prove_absent",side_effect=race), patch(
                "urano.restricted_systemd_broker.CGROUP_ROOT",self.root/"cg"):
            outcome=broker.reconcile_on_authoritative_start()
        self.assertEqual(outcome,{"preserved":1,"released_absent":0,"uncertain":1})
        self.assertEqual(self.ledger.get_trusted(self.first.job_id).state,"orphaned")
        self.assertEqual(self.ledger.get_trusted(self.second.job_id).state,"running")
        self.systemd.stop_exact.assert_not_called()

    def test_confirm_absent_rejects_unsigned_kernel_proof(self):
        current=self.ledger.get_trusted(self.first.job_id)
        with self.assertRaises(ValueError):
            self.ledger.confirm_absent_on_daemon_start(
                current,verified_cgroup_empty=False)
        self.assert_both_running()


class ExclusiveBroker305(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="montara-broker-lock-305-")
        self.addCleanup(t.cleanup)
        self.root=Path(t.name).resolve()
        self.a=self.root/"ledger.sqlite3"

    def test_only_one_authoritative_daemon_per_ledger(self):
        with exclusive_broker_daemon(self.a):
            with self.assertRaises(BrokerAlreadyActive):
                with exclusive_broker_daemon(self.a):
                    pass
        with exclusive_broker_daemon(self.a):
            pass

    def test_exclusive_lock_is_respected_across_real_processes(self):
        # Separate Python process (not merely two descriptors in one PID).
        child_source = (
            "import sys, time\n"
            "from pathlib import Path\n"
            "from urano.broker_daemon_guard import exclusive_broker_daemon\n"
            "with exclusive_broker_daemon(Path(sys.argv[1])):\n"
            " print('LOCKED',flush=True)\n"
            " time.sleep(6)\n"
        ).replace("\\n", "\n")
        child = subprocess.Popen(
            [sys.executable, "-c", child_source, str(self.a)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            ready = child.stdout.readline().strip()
            if ready != "LOCKED":
                details = child.stderr.read(800)
                self.fail("Child failed to lock: " + details)
            with self.assertRaises(BrokerAlreadyActive):
                with exclusive_broker_daemon(self.a):
                    pass
        finally:
            child.terminate()
            child.wait(timeout=5)
            child.stdout.close()
            child.stderr.close()
        with exclusive_broker_daemon(self.a):
            pass

    def test_existing_lock_symlink_refused(self):
        outside=self.root/"elsewhere"
        outside.write_text("do not touch")
        (self.root/"authoritative-daemon.lock").symlink_to(outside)
        with self.assertRaises((OSError,RuntimeError)):
            with exclusive_broker_daemon(self.a):pass
        self.assertEqual(outside.read_text(),"do not touch")

    def test_socket_in_use_refused_without_unlink(self):
        p=self.root/"control.sock"
        server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            server.bind(str(p))
            server.listen(1)
            with self.assertRaises(BrokerAlreadyActive):
                refuse_live_broker_socket(p)
            self.assertTrue(p.exists())
        finally:
            server.close()

    def test_stale_socket_can_be_replaced_only_under_lease(self):
        p=self.root/"control.sock"
        server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        server.bind(str(p))
        server.close()
        with exclusive_broker_daemon(self.a):
            refuse_live_broker_socket(p)
        self.assertTrue(p.exists())

    def test_suspicious_path_refused(self):
        x=self.root/"control.sock"
        x.write_text("not a socket")
        with self.assertRaises(RuntimeError):
            refuse_live_broker_socket(x)

    def test_daemon_only_entrypoint_calls_reconciliation(self):
        import inspect
        from urano.private_broker_service import main
        text=inspect.getsource(main)
        self.assertLess(text.index("with exclusive_broker_daemon(ledger_path)"),
                        text.index("broker=DemoBroker("))
        self.assertLess(text.index("refuse_live_broker_socket(broker_socket)"),
                        text.index("broker_socket.unlink()"))
        self.assertLess(text.index("broker=DemoBroker("),
                        text.index("broker.reconcile_on_authoritative_start()"))


if __name__=="__main__":
    unittest.main()
