"""Regression: Windows native Companion explicitly allows the three beta portals.

Extract the same C# regex pieces passed to MONTARA_COMPANION_ORIGINS.
This test does not launch or replace the habitual Companion.
"""
from pathlib import Path
import re
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "companion" / "windows_native" / "BundledService.cs"

def runtime_origin_pattern():
    src = SOURCE.read_text(encoding="utf-8")
    tail = src.split('start.Environment["MONTARA_COMPANION_ORIGINS"] =', 1)[1].split(";", 1)[0]
    chunks = re.findall(r'@"([^"]+)"', tail)
    assert len(chunks) >= 4, "missing explicit C# origin fragments"
    return re.compile(r"^(?:" + "".join(chunks) + r")$")

class WindowsCompanionOrigins(unittest.TestCase):
    def test_three_beta_portals_allowed(self):
        pattern = runtime_origin_pattern()
        for site in ("montara-lab-fer", "montara-lab-jm", "montara-main"):
            with self.subTest(site=site):
                self.assertIsNotNone(pattern.fullmatch(f"https://{site}.memoriainvalida001.workers.dev"))

    def test_legacy_origin_remains_available_until_migration(self):
        pattern = runtime_origin_pattern()
        for site in ("montara-owner", "montara-owner-h4"):
            with self.subTest(site=site):
                self.assertIsNotNone(pattern.fullmatch(f"https://{site}.memoriainvalida001.workers.dev"))

    def test_localhost_retained(self):
        pattern = runtime_origin_pattern()
        for value in ("http://127.0.0.1:8102", "http://localhost:47820", "https://localhost"):
            with self.subTest(value=value):
                self.assertIsNotNone(pattern.fullmatch(value))

    def test_untrusted_origins_rejected(self):
        pattern = runtime_origin_pattern()
        for value in (
            "https://evil.memoriainvalida001.workers.dev",
            "https://montara-main.evil.example",
            "https://montara-main.memoriainvalida001.workers.dev.evil.example",
            "http://montara-main.memoriainvalida001.workers.dev",
            "https://montara-main.memoriainvalida001.workers.dev:444",
            "https://montara-main.memoriainvalida001.workers.dev@evil.example",
            "https://montara-main.memoriainvalida001.workers.dev/extra",
            "null", "", "https://montara-lab-jm.memoriainvalida001.workers.dev.evil.test",
        ):
            with self.subTest(value=value):
                self.assertIsNone(pattern.fullmatch(value))

if __name__ == "__main__":
    unittest.main()
