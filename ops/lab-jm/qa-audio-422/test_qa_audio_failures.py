import errno
import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('qa_audio_failures',HERE/'qa_audio_failures.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class AudioErrors(unittest.TestCase):
 def test_permanent(self):
  for exc,status,code in [(ValueError('secret'),422,'AUDIO_INVALID_REQUEST'),
        (PermissionError('secret'),403,'AUDIO_AUTH_DENIED'),
        (FileNotFoundError('secret'),404,'AUDIO_ORIGINAL_MISSING'),
        (RuntimeError('secret'),422,'AUDIO_PREPARATION_FAILED'),
        (OSError(errno.ENOSPC,'secret'),507,'AUDIO_INSUFFICIENT_STORAGE')]:
   with self.subTest(code=code):
    result,body=mod.safe_audio_error(exc)
    self.assertEqual((result,body['code'],body['retryable']),(status,code,False))
    self.assertNotIn('secret',str(body))
 def test_temporary(self):
  for exc in (TimeoutError('secret'), OSError(errno.EAGAIN,'secret'),OSError(errno.ECONNRESET,'secret')):
   status,body=mod.safe_audio_error(exc)
   self.assertEqual(status,503);self.assertTrue(body['retryable'])
   self.assertNotIn('secret',str(body))
 def test_generic_is_fail_closed(self):
  status,body=mod.safe_audio_error(KeyError('/private/path'))
  self.assertEqual(status,422);self.assertFalse(body['retryable'])
  self.assertNotIn('/private/path',str(body))
 def test_patcher_rejects_unreviewed_source(self):
  spec=importlib.util.spec_from_file_location('qa_patch',HERE/'patch_qa.py')
  patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
  with tempfile.TemporaryDirectory() as td:
   src=Path(td)/'unreviewed.py';src.write_text('print(123)')
   with self.assertRaises(ValueError):patch.patch(src,Path(td)/'out')
   self.assertFalse((Path(td)/'out'/'companion.py').exists())

if __name__=='__main__':unittest.main()
