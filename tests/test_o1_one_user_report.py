"""Tests for O1 one-user aggregation; no network, media or running services."""
import unittest

from o1_hybrid_node_meter import build_report
from o1_one_user_report import combine_one_user


def node(host, role, run="test-one"):
    sample = {
        "method": "psutil-pid-tree-sampled", "observation_seconds": 1.5,
        "samples": 3, "cpu_seconds_observed_lower_bound": 0.12,
        "rss_bytes_sampled_peak": 500000,
    }
    return build_report(run_id=run, physical_host_label=host, role=role,
                        scenario_clients=1, results=sample)


class OneUserReportContracts(unittest.TestCase):
    def test_separate_companion_vm_and_optional_browser(self):
        data = combine_one_user([node("win-a", "client_companion"),
                                 node("gcp-b", "server"),
                                 node("win-a", "client_browser")], operator_verified=True)
        self.assertEqual(data["scenario_clients"], 1)
        self.assertEqual(len(data["meters"]), 3)
        self.assertTrue(data["physical_hosts_operator_verified"])
        self.assertFalse(data["distributed_performance_verified"])
        self.assertFalse(data["completed_stage_e2e_verified"])
        self.assertFalse(data["original_upload_proven_absent"])
        self.assertIsNone(data["WAN_bytes_measured"])

    def test_reject_missing_or_duplicate_or_same_host(self):
        good = [node("win-a", "client_companion"), node("gcp-b", "server")]
        bad_cases = [
            good[:1],
            good + [node("win-b", "client_companion")],
            [good[0], node("win-a", "server")],
            [good[0], node("gcp-b", "server", run="other")],
            [good[0], node("gcp-b", "client_browser")],
        ]
        for case in bad_cases:
            with self.subTest(size=len(case)):
                with self.assertRaises(ValueError):
                    combine_one_user(case)

    def test_reject_fabricated_or_malformed_sample(self):
        good = [node("win-a", "client_companion"), node("gcp-b", "server")]
        for key, value in (("samples", 0),
                           ("cpu_seconds_observed_lower_bound", -1),
                           ("rss_bytes_sampled_peak", float("nan"))):
            import copy
            bad = copy.deepcopy(good)
            bad[0]["sample"][key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                combine_one_user(bad)
        good[0]["no_media_or_secrets_collected"] = False
        with self.assertRaises(ValueError):
            combine_one_user(good)

    def test_only_one_client_accepted_by_meter(self):
        report = node("win-a", "client_companion")
        self.assertEqual(report["scenario_clients"], 1)
        self.assertFalse(report["remote_server_verified"])
        with self.assertRaises(ValueError):
            build_report(run_id="x", physical_host_label="win-a", role="server",
                         scenario_clients=3, results=report["sample"])


if __name__ == "__main__":
    unittest.main()
