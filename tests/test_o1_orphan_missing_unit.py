"""O1 focused regression: existing broker recovers absent transient units safely.

Uses temporary JobRecoveryLedger, mocked systemd and temporary cgroup root.
No production jobs, services or database writes.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from urano.job_recovery_ledger import JobRecoveryLedger
from urano.restricted_systemd_broker import RestrictedTargetControl, UnverifiedTarget


def orphaned(root: str):
    ledger = JobRecoveryLedger(Path(root) / "jobs.sqlite3")
    lease = ledger.start_trusted("owner-a", "project-a")
    ledger.reserve_target_unit(lease)
    return ledger, ledger.recover_after_restart()[0]


def absent_state():
    return {
        "LoadState": "not-found", "ActiveState": "inactive",
        "SubState": "dead", "ControlGroup": "", "MainPID": "0"
    }


class MissingUnitAfterReboot(unittest.TestCase):
    def test_double_verified_absent_unit_can_be_released_by_existing_ledger(self):
        with tempfile.TemporaryDirectory(prefix="o1-recovery-") as root:
            ledger, orphan = orphaned(root)
            systemd = Mock()
            systemd.show.return_value = absent_state()
            with patch("urano.restricted_systemd_broker.CGROUP_ROOT", Path(root) / "missing-cgroup"):
                verified = RestrictedTargetControl(ledger, systemd).stop_verified(orphan)
            self.assertTrue(verified)
            self.assertEqual(systemd.show.call_count, 2)
            systemd.stop_exact.assert_not_called()
            ledger.confirm_stopped(ledger.request_stop(orphan), verified_cgroup_empty=verified)
            self.assertEqual(ledger.unverified_for_owner("owner-a"), ())

    def test_missing_unit_reappearing_between_checks_is_denied(self):
        with tempfile.TemporaryDirectory(prefix="o1-recovery-") as root:
            ledger, orphan = orphaned(root)
            systemd = Mock()
            changed = {**absent_state(), "ActiveState": "active"}
            systemd.show.side_effect = [absent_state(), changed]
            with patch("urano.restricted_systemd_broker.CGROUP_ROOT", Path(root) / "missing-cgroup"):
                with self.assertRaises(UnverifiedTarget):
                    RestrictedTargetControl(ledger, systemd).stop_verified(orphan)
            self.assertEqual(ledger.unverified_for_owner("owner-a")[0].state, "orphaned")
            systemd.stop_exact.assert_not_called()

    def test_absent_unit_with_still_present_cgroup_is_denied(self):
        with tempfile.TemporaryDirectory(prefix="o1-recovery-") as root:
            ledger, orphan = orphaned(root)
            systemd = Mock()
            systemd.show.return_value = absent_state()
            fake_cgroup = Path(root) / "cgroups"
            target = ledger.target_for_trusted(orphan)
            (fake_cgroup / "system.slice" / (target + ".service")).mkdir(parents=True)
            with patch("urano.restricted_systemd_broker.CGROUP_ROOT", fake_cgroup):
                with self.assertRaises(UnverifiedTarget):
                    RestrictedTargetControl(ledger, systemd).stop_verified(orphan)
            systemd.stop_exact.assert_not_called()
            self.assertEqual(ledger.unverified_for_owner("owner-a")[0].state, "orphaned")

    def test_unobservable_or_ambiguous_state_never_counts_as_absent(self):
        with tempfile.TemporaryDirectory(prefix="o1-recovery-") as root:
            ledger, orphan = orphaned(root)
            with patch("urano.restricted_systemd_broker.CGROUP_ROOT", Path(root) / "missing-cgroup"):
                for key, value in (("MainPID", "1"), ("LoadState", None),
                                   ("ControlGroup", "/system.slice/other.service"),
                                   ("SubState", "running"), ("ActiveState", "failed")):
                    state = absent_state()
                    state[key] = value
                    systemd = Mock()
                    systemd.show.return_value = state
                    with self.subTest(key=key), self.assertRaises(UnverifiedTarget):
                        RestrictedTargetControl(ledger, systemd).stop_verified(orphan)
                    systemd.stop_exact.assert_not_called()
            self.assertEqual(ledger.unverified_for_owner("owner-a")[0].state, "orphaned")

    def test_unrelated_owner_keeps_independent_slot(self):
        with tempfile.TemporaryDirectory(prefix="o1-recovery-") as root:
            ledger, orphan = orphaned(root)
            other = ledger.start_trusted("owner-b", "project-b")
            self.assertEqual(other.generation, 1)
            self.assertEqual(ledger.unverified_for_owner("owner-a")[0].state, "orphaned")


if __name__ == "__main__":
    unittest.main()
