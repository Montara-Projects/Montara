"""Actual localhost HTTP preflight on an ephemeral isolated Companion server.

The origin regex comes from the Windows C# launcher, not a separate test fixture.
No FFmpeg, main Companion, login, media, real port or cloud service is touched.
"""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from test_windows_companion_origin_policy import runtime_origin_pattern

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "companion"))


class CompanionThreeOriginsHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix="montara-cors-http-")
        original = os.environ.get("MONTARA_COMPANION_HOME")
        os.environ["MONTARA_COMPANION_HOME"] = cls.scratch.name
        try:
            spec = importlib.util.spec_from_file_location(
                "companion_three_origin_http_fixture", ROOT / "companion/companion.py"
            )
            cls.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.module)
        finally:
            if original is None:
                os.environ.pop("MONTARA_COMPANION_HOME", None)
            else:
                os.environ["MONTARA_COMPANION_HOME"] = original
        cls.module.ORIGINS = runtime_origin_pattern()
        cls.server = cls.module.ThreadingHTTPServer(("127.0.0.1", 0), cls.module.Handler)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        cls.root = "http://127.0.0.1:%s" % cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=5)
        cls.scratch.cleanup()

    def request(self, method, path, origin=None, host=None):
        headers = {"Access-Control-Request-Method": "POST",
                   "Access-Control-Request-Private-Network": "true"}
        if origin is not None:
            headers["Origin"] = origin
        if host is not None:
            headers["Host"] = host
        request = Request(self.root + path, method=method, headers=headers)
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, response.headers
        except HTTPError as error:
            return error.code, error.headers

    def test_three_authorized_preflights_return_exact_origin_and_pna(self):
        for site in ("montara-lab-fer", "montara-lab-jm", "montara-main"):
            origin = "https://%s.memoriainvalida001.workers.dev" % site
            with self.subTest(origin=origin):
                status, headers = self.request("OPTIONS", "/video-renders", origin)
                self.assertEqual(status, 204)
                self.assertEqual(headers.get("Access-Control-Allow-Origin"), origin)
                self.assertEqual(headers.get("Access-Control-Allow-Private-Network"), "true")
                self.assertIn("Origin", headers.get("Vary", ""))

    def test_unknown_and_missing_origin_cannot_preflight_or_post(self):
        for origin in (None, "null",
                       "https://unrelated.memoriainvalida001.workers.dev",
                       "https://montara-main.memoriainvalida001.workers.dev.attacker.invalid"):
            with self.subTest(origin=origin):
                for method in ("OPTIONS", "POST"):
                    status, headers = self.request(method, "/video-renders", origin)
                    self.assertEqual(status, 403)
                    self.assertIsNone(headers.get("Access-Control-Allow-Origin"))
                    self.assertIsNone(headers.get("Access-Control-Allow-Private-Network"))

    def test_metadata_health_remains_unprotected_by_origin(self):
        status, headers = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertIsNone(headers.get("Access-Control-Allow-Origin"))

    def test_malicious_host_denied_on_health_preflight_and_job_route(self):
        legitimate = "https://montara-lab-fer.memoriainvalida001.workers.dev"
        for host in ("attacker.invalid", "127.0.0.1:1", "127.0.0.1",
                     "127.0.0.1.%s.attacker.invalid" % self.server.server_port,
                     "localhost.attacker.invalid:%s" % self.server.server_port):
            for method, path in (("GET", "/health"), ("OPTIONS", "/video-renders"),
                                 ("POST", "/video-renders"),
                                 ("GET", "/video-renders/" + "0"*32)):
                with self.subTest(host=host, method=method, path=path):
                    status, headers = self.request(method, path, legitimate, host=host)
                    self.assertEqual(status, 403)
                    self.assertIsNone(headers.get("Access-Control-Allow-Origin"))

    def test_exact_local_host_aliases_accepted(self):
        for host in ("localhost:%s" % self.server.server_port,
                     "127.0.0.1:%s" % self.server.server_port):
            with self.subTest(host=host):
                status, headers = self.request(
                    "OPTIONS", "/video-renders",
                    "https://montara-main.memoriainvalida001.workers.dev", host=host)
                self.assertEqual(status, 204)

    def test_other_get_without_origin_rejected(self):
        status, headers = self.request("GET", "/video-renders/" + "0"*32)
        self.assertEqual(status, 403)
        self.assertIsNone(headers.get("Access-Control-Allow-Origin"))


if __name__ == "__main__":
    unittest.main()
