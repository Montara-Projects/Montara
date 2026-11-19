"""Generation fenced Owner Engine close: no systemd or live VM access."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from urano.private_broker_service import DemoBroker
from urano.job_recovery_ledger import StaleJob, BusyOwner
from urano.private_stage_owner_admission import verify_stage_owner_request
from urano.project_catalog import ProjectCatalog
from urano.session_auth import SessionStore


class SafeOwnerCloseTests(unittest.TestCase):
    def test_broker_must_reject_stale_generation_without_touching_current_worker(self):
        current = SimpleNamespace(project_id="project-a", generation=8, state="running")
        class Ledger:
            def __init__(self):
                self.stop_requested = 0
                self.confirmed = 0

            def unverified_for_owner(self, owner):
                return [current] if owner == "owner-a" else []

            def request_stop(self, lease):
                self.stop_requested += 1
                return lease

            def confirm_stopped(self, lease, *, verified_cgroup_empty):
                assert verified_cgroup_empty is True
                self.confirmed += 1

        class Control:
            def __init__(self):
                self.stop_calls = 0

            def stop_verified(self, lease):
                self.stop_calls += 1
                return True

        broker = object.__new__(DemoBroker)
        broker.ledger = Ledger()
        broker.control = Control()
        for generation in (7, 9, True, None):
            if generation is None:
                continue  # Backward-compatible admin close without fencing.
            with self.subTest(generation=generation):
                with self.assertRaises(StaleJob):
                    broker.stop_owner("owner-a", "project-a", expected_generation=generation)
        with self.assertRaises(StaleJob):
            broker.stop_owner("owner-b", "project-a", expected_generation=8)
        with self.assertRaises(StaleJob):
            broker.stop_owner("owner-a", "project-b", expected_generation=8)
        self.assertEqual(broker.ledger.stop_requested, 0)
        self.assertEqual(broker.control.stop_calls, 0)

        # Two tabs can have the same Owner/project/generation. The broker
        # cannot know which is still editing; do not stop on this evidence.
        for _tab in ("tab-with-finished-mp4", "tab-still-editing"):
            with self.subTest(tab=_tab), self.assertRaises(BusyOwner):
                broker.stop_owner("owner-a", "project-a", expected_generation=8)
        self.assertEqual(broker.ledger.stop_requested, 0)
        self.assertEqual(broker.control.stop_calls, 0)
        self.assertEqual(broker.ledger.confirmed, 0)

        # Unfenced operator stop remains available after independent operator
        # verification. It is NOT callable from the native browser /close API.
        result = broker.stop_owner("owner-a", "project-a")
        self.assertEqual(result["state"], "stopped")
        self.assertEqual(broker.ledger.stop_requested, 1)
        self.assertEqual(broker.control.stop_calls, 1)
        self.assertEqual(broker.ledger.confirmed, 1)

    def test_new_privileged_close_frame_revalidates_session_csrf_owner_and_generation(self):
        with tempfile.TemporaryDirectory(prefix="montara-owner-close-") as tmp:
            root = Path(tmp)
            catalog = ProjectCatalog(root / "projects.sqlite3")
            sessions = SessionStore(root / "sessions.sqlite3")
            own = sessions.issue("owner-a")
            foreign = sessions.issue("owner-b")
            project = catalog.create("owner-a", "Stage").id

            def frame(session, csrf, generation, project_id=project):
                return json.dumps({
                    "op": "close_generation_owner", "session": session,
                    "csrf": csrf, "project_id": project_id,
                    "generation": generation
                }).encode()

            self.assertEqual(
                verify_stage_owner_request(frame(own.token, own.csrf, 8),
                    owner_db_root=root, operation="close_generation_owner"),
                ("owner-a", project, 8))
            bad = [
                frame(foreign.token, foreign.csrf, 8),
                frame(own.token, foreign.csrf, 8),
                frame(own.token, own.csrf, 0),
                frame(own.token, own.csrf, True),
                frame(own.token, own.csrf, 2**31),
            ]
            for forged in bad:
                with self.subTest(forged=forged[-32:]):
                    with self.assertRaises((ValueError, PermissionError)):
                        verify_stage_owner_request(forged, owner_db_root=root,
                                                   operation="close_generation_owner")
            with self.assertRaises(ValueError):
                verify_stage_owner_request(frame(own.token, own.csrf, 8),
                                           owner_db_root=root)
            with self.assertRaises(ValueError):
                verify_stage_owner_request(frame(own.token, own.csrf, 8),
                                           owner_db_root=root, operation="foo")


if __name__ == "__main__":
    unittest.main()
