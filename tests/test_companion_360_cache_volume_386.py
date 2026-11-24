"""Guard project-volume spherical cache against cross-device hard-link regression."""
import importlib.util
import errno
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

class Cached360(unittest.TestCase):
    def test_cache_path_matches_work_folder(self):
        source=(ROOT/'companion/video_jobs.py').read_text()
        self.assertIn("'spherical_cache':str(folder/'.montara-renders'/'.spherical-cache'/runtime['engine'])",source)
        self.assertNotIn("'spherical_cache':str(self.home/'spherical-cache'/runtime['engine'])",source)

    def test_retain_restore_exact_file_same_volume(self):
        spec=importlib.util.spec_from_file_location('montara_local_video_cache',ROOT/'companion/local_video.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'render-work'/'Cache'/'spherical_export'/('equirect-'+'a'*24+'.mp4')
            src.parent.mkdir(parents=True);src.write_bytes(b'synthetic-high-quality-intermediate-001')
            cache=root/'.montara-renders'/'.spherical-cache'/'engine-version'
            self.assertEqual(module.retain_spherical_cache(cache,{src}),1)
            entry=cache/src.name
            self.assertEqual(entry.read_bytes(),src.read_bytes())
            self.assertEqual(src.stat().st_ino,entry.stat().st_ino)
            src.unlink()
            self.assertEqual(module.retain_spherical_cache(cache,{src},restore=True),1)
            self.assertEqual(src.read_bytes(),b'synthetic-high-quality-intermediate-001')
            self.assertEqual(src.stat().st_ino,entry.stat().st_ino)

    def test_exfat_unsupported_link_uses_atomic_copy(self):
        spec=importlib.util.spec_from_file_location('montara_exfat_cache',ROOT/'companion/local_video.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/('equirect-'+'c'*24+'.mp4')
            source.write_bytes(b'test-360-video' * 10000)
            cache=root/'cache'
            with patch.object(module.os,'link',side_effect=OSError(errno.ENOTSUP,'Hard links not supported')):
                self.assertEqual(module.retain_spherical_cache(cache,{source}),1)
            cached=cache/source.name
            self.assertEqual(source.read_bytes(),cached.read_bytes())
            self.assertFalse(any(cache.glob('*.part')))
            source.unlink()
            with patch.object(module.os,'link',side_effect=OSError(errno.ENOTSUP,'Hard links not supported')):
                self.assertEqual(module.retain_spherical_cache(cache,{source},restore=True),1)
            self.assertEqual(source.read_bytes(),cached.read_bytes())

    def test_skip_symbolic_or_partial_files(self):
        spec=importlib.util.spec_from_file_location('montara_local_video_cache2',ROOT/'companion/local_video.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cached=root/'cache';original=root/'file.mp4';original.write_bytes(b'bytes')
            symlink=root/('equirect-'+'b'*24+'.mp4');symlink.symlink_to(original)
            self.assertEqual(module.retain_spherical_cache(cached,{symlink}),0)
            self.assertFalse((cached/symlink.name).exists())
            invalid=root/('equirect-'+'a'*24+'.mp4');invalid.write_bytes(b'')
            self.assertEqual(module.retain_spherical_cache(cached,{invalid}),0)

if __name__=='__main__':unittest.main()
