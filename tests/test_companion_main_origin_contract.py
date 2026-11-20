"""Static security contract for Windows MAIN Companion origins."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class WindowsMainOriginContract(unittest.TestCase):
    def test_compiled_origin_regex_matches_only_reviewed_hosts(self):
        source = (ROOT / "companion/windows_native/BundledService.cs").read_text()
        segment = source.split('start.Environment["MONTARA_COMPANION_ORIGINS"] =', 1)[1].split(';', 1)[0]
        fragments = re.findall(r'@"([^"]+)"', segment)
        self.assertEqual(len(fragments), 5)
        rule = re.compile('^(' + ''.join(fragments) + ')$')
        for host in ('montara-main', 'montara-owner-h4', 'montara-lab-fer', 'montara-owner'):
            self.assertIsNotNone(rule.fullmatch('https://' + host + '.memoriainvalida001.workers.dev'))
        for url in ('https://fake-montara-main.memoriainvalida001.workers.dev',
                    'http://montara-main.memoriainvalida001.workers.dev',
                    'https://montara-main.memoriainvalida001.workers.dev.evil.test',
                    'https://other.workers.dev', 'https://montara-main.memoriainvalida001.workers.dev:444'):
            self.assertIsNone(rule.fullmatch(url))
    def test_dashboard_opens_main_without_repinning_unverified_local_engine(self):
        source = (ROOT / 'companion/windows_native/Program.cs').read_text()
        self.assertIn('private const string BetaUrl = "https://montara-main.memoriainvalida001.workers.dev/";',source)
        self.assertIn('PinnedEngine = "b867b3c72af8fe4685b487bcf1e09ffcc2a7c82b"',source)
