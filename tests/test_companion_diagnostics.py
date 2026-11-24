"""Issue #343: non-destructive Companion diagnostics and classifications."""
import sys
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'companion'))
from media_diagnostics import classify_probe, diagnose_video


def probe(duration='10.5',codec='h264',video=True):
    return json.dumps({'format':{'duration':duration},'streams':
        ([{'codec_type':'video','codec_name':codec,'width':1920,'height':1080}] if video else [])})


class DiagnosticContractTests(unittest.TestCase):
    def test_healthy_short_video_is_not_damaged(self):
        value=classify_probe(returncode=0,stdout=probe('1.92'))
        self.assertEqual((value['status'],value['reason']),('healthy','short_clip'))
        self.assertFalse(value['repair_offer'])

    def test_missing_moov_is_repair_candidate(self):
        value=classify_probe(returncode=1,stdout='',stderr='moov atom not found')
        self.assertEqual((value['status'],value['reason']),('damaged','missing_index'))
        self.assertTrue(value['repair_offer'])

    def test_unreadable_without_clear_damage_not_claimed_repairable(self):
        self.assertEqual(classify_probe(returncode=1,stdout='',stderr='permission denied')['status'],'inconclusive')

    def test_unsupported_codec_not_corruption(self):
        self.assertEqual(classify_probe(returncode=0,stdout=probe(codec='magic'))['status'],'unsupported')

    def test_audio_only_not_corruption(self):
        self.assertEqual(classify_probe(returncode=0,stdout=probe(video=False))['status'],'unsupported')

    def test_empty_bad_json_inconclusive(self):
        self.assertEqual(classify_probe(returncode=0,stdout='{')['status'],'inconclusive')

    def test_timeout_inconclusive(self):
        self.assertEqual(classify_probe(returncode=-1,stdout='',timed_out=True)['reason'],'probe_timeout')

    def test_real_file_kept_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'original.mp4';file.write_bytes(b'original_bytes')
            class Result:
                returncode=1
                stdout=''
                stderr='moov atom not found'
            with patch('media_diagnostics.subprocess.run',return_value=Result()) as run:
                diagnosis=diagnose_video(file,ffprobe='ffprobe')
            self.assertEqual(diagnosis['status'],'damaged')
            self.assertEqual(file.read_bytes(),b'original_bytes')
            self.assertEqual(run.call_args.kwargs['timeout'],30.0)
            self.assertEqual(list(Path(d).iterdir()),[file])

    def test_unsupported_file_never_runs_external_command(self):
        with patch('media_diagnostics.subprocess.run') as run:
            out=diagnose_video(Path('/tmp/nonexistent.pdf'),ffprobe='ffprobe')
        self.assertEqual(out['reason'],'unsupported_extension')
        run.assert_not_called()

if __name__=='__main__':unittest.main()
