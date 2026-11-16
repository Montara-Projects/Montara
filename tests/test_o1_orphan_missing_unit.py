"""O1 regression characterization: an absent systemd unit must not be auto-released.

Reuses existing ledger and RestrictedTargetControl. Temporary SQLite and a
fake systemd adapter only; never reads production data or stops a real unit.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from urano.job_recovery_ledger import JobRecoveryLedger
from urano.restricted_systemd_broker import RestrictedTargetControl


class MissingUnitAfterReboot(unittest.TestCase):
    def test_missing_unit_stop_command_failure_keeps_orphan_fenced(self):
        """Capture *current* fail-closed behavior without proposing SQL cleanup."""
        with tempfile.TemporaryDirectory(prefix="o1-recovery-fixture-") as root:
            ledger = JobRecoveryLedger(Path(root) / "jobs.sqlite3")
            lease = ledger.start_trusted("owner-a", "project-a")
            ledger.reserve_target_unit(lease)
            orphan = ledger.recover_after_restart()[0]
            self.assertEqual(orphan.state, "orphaned")
            systemd = Mock()
            systemd.show.return_value = {
                "LoadState": "not-found", "ActiveState": "inactive",
                "ControlGroup": "", "MainPID": "0",
            }
            systemd.stop_exact.side_effect = subprocess.CalledProcessError(
                returncode=5, cmd=["systemctl", "stop", "<missing-unit>"])
            control = RestrictedTargetControl(ledger, systemd)
            with self.assertRaises(subprocess.CalledProcessError):
                control.stop_verified(orphan)
            systemd.stop_exact.assert_called_once()
            self.assertEqual(
                [j.state for j in ledger.unverified_for_owner("owner-a")],
                ["orphaned"],
            )
            # Unrelated owner can still obtain a distinct reservation.
            other = ledger.start_trusted("owner-b", "project-b")
            self.assertEqual(other.generation, 1)

    def test_mismatched_cgroup_rejected_before_stop(self):
        with tempfile.TemporaryDirectory(prefix="o1-recovery-fixture-") as root:
            ledger = JobRecoveryLedger(Path(root) / "jobs.sqlite3")
            lease = ledger.start_trusted("owner-a", "project-a")
            ledger.reserve_target_unit(lease)
            orphan = ledger.recover_after_restart()[0]
            systemd = Mock()
            systemd.show.return_value = {
                "LoadState": "loaded", "ActiveState": "active",
                "ControlGroup": "/system.slice/unrelated.service",
            }
            with self.assertRaises(Exception):
                RestrictedTargetControl(ledger, systemd).stop_verified(orphan)
            systemd.stop_exact.assert_not_called()
            self.assertEqual(
                ledger.unverified_for_owner("owner-a")[0].state, "orphaned"
            )


if __name__ == "__main__":
    unittest.main()
