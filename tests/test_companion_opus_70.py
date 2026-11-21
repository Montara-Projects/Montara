"""The new Opus transport policy is 70%, without changing source/master fidelity."""
from __future__ import annotations
import importlib.util
import pathlib
import sys
import tempfile
import os
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'companion'))
with patch.dict(os.environ,{'MONTARA_COMPANION_HOME':tempfile.mkdtemp(prefix='opus70-')}):
    import companion as cp

class Opus70Tests(unittest.TestCase):
    def test_preview_bitrates(self):
        self.assertEqual(cp.OPUS_PREVIEW_PERCENT,70)
        self.assertEqual(cp.opus_preview_kbps(96),67)
        self.assertEqual(cp.opus_preview_kbps(192),134)
        self.assertEqual(cp.opus_preview_kbps(256),179)
        command=cp.preview_command(pathlib.Path('test.wav'),pathlib.Path('preview.opus'),
                                   {'channels':2,'rate':'48000','bits':'16'})
        self.assertEqual(command[command.index('-b:a')+1],'134k')
        self.assertIn('montara_sample_rate=48000',command)
    def test_proxy_cache_requires_new_recipe(self):
        root=pathlib.Path(tempfile.mkdtemp(prefix='opus70-cache-'))
        src=root/'source.wav'
        src.write_bytes(b'RIFF'+b'0'*256)
        key='a'*24+'p'
        output=root/'preview.opus'
        output.write_bytes(b'OggS'+b'0'*256)
        with patch.dict(cp.sources,{'a'*24:src}):
            self.assertFalse(cp.proxy_cache_valid(key,output))
            output.with_suffix('.quality.json').write_text('{"opus_preview_percent":70}')
            self.assertTrue(cp.proxy_cache_valid(key,output))

if __name__=='__main__':
    unittest.main()
