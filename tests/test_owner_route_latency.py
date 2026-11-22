"""Safe Owner log parser contract; no real user journal or private paths."""
import json
import unittest

from scripts.diagnostics.owner_route_latency import aggregate, route_id


class OwnerRouteLatencyTest(unittest.TestCase):
    def test_discard_tokens_and_private_names(self):
        events = [
            'Slow request GET /api/v1/wizard/review?render=0&token=SENSITIVE: 5937.4 ms (HTTP 200)\n',
            '<local> - - [x] "GET /api/v1/wizard/review?render=0&token=SENSITIVE HTTP/1.1" 200 -\n',
            'Slow request GET /api/v1/wizard/review/preview/122?secret=SENSITIVE: 42789.2 ms (HTTP 503)\n',
            '<local> "GET /api/v1/wizard/review/preview/122?secret=SENSITIVE HTTP/1.1" 503 -\n',
            'Slow request PATCH /api/v1/edit/shot?project=/private/T4T: 3051.1 ms (HTTP 409)\n',
            '<local> "PATCH /api/v1/edit/shot?path=private-filename HTTP/1.1" 409 -\n',
            '<local> "GET /media/private/path?token=SENSITIVE HTTP/1.1" 200 -\n',
        ]
        payload = aggregate(events, "JM")
        output = json.dumps(payload)
        for token in ("SENSITIVE", "private-filename", "/private/T4T", "122"):
            self.assertNotIn(token, output)
        self.assertEqual(payload["routes"]["GET review"]["access_status_counts"], {"200": 1})
        self.assertEqual(payload["routes"]["GET review"]["slow_sample_median_ms"], 5937.4)
        self.assertEqual(payload["routes"]["GET hover_preview"]["access_status_counts"], {"503": 1})
        self.assertEqual(payload["routes"]["PATCH edit_shot"]["access_status_counts"], {"409": 1})
        self.assertNotIn("slow_sample_p95_ms", payload["routes"]["GET review"])

    def test_disallow_unknown_routes_and_many_sample_p95(self):
        self.assertIsNone(route_id("DELETE", "/api/v1/edit/shot"))
        self.assertIsNone(route_id("GET", "/api/v1/wizard/review/preview/nonint"))
        self.assertIsNone(route_id("GET", "/api/v1/session/private"))
        lines = [
            f"Slow request GET /api/v1/wizard/review: {2000+i*100}.0 ms (HTTP 200)"
            for i in range(20)
        ]
        result = aggregate(lines, "FER")["routes"]["GET review"]
        self.assertEqual(result["slow_samples_only"], 20)
        self.assertGreaterEqual(result["slow_sample_p95_ms"], 3800)
        self.assertLessEqual(result["slow_sample_p95_ms"], result["slow_sample_max_ms"])


if __name__ == "__main__":
    unittest.main()
