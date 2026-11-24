"""Prepare an off-line QA-only patch; NEVER edits a live Companion installation.

Usage: python3 patch_qa.py INPUT_COMPANION_PY OUTPUT_DIRECTORY
The input must match the explicitly reviewed LAB-JM QA source hash.
"""
from __future__ import annotations
import hashlib
import shutil
import sys
from pathlib import Path

REVIEWED_SHA256 = '35e1a60dc348cb003b595452674861fa9770a90d9ca6f39f529b27ace11c8c3c'
OLD = """        except PermissionError:return self.reply(403,{'error':'QA audio authorization denied or expired'})
        except FileNotFoundError:return self.reply(404,{'error':'Unknown QA audio job'})
        except (ValueError,OSError,RuntimeError,KeyError,URLError):return self.reply(422,{'error':'QA could not complete this audio operation. Originals remain on this Mac.'})"""
TIMEOUT_OLD = "raise RuntimeError('Audio preparation timed out; the original remains on this Mac')"
TIMEOUT_NEW = "raise TimeoutError('Audio preparation timed out; the original remains on this Mac')"
NEW = """        except PermissionError:return self.reply(403,{'error':'QA audio authorization denied or expired','code':'AUDIO_AUTH_DENIED','retryable':False})
        except FileNotFoundError:return self.reply(404,{'error':'Original or QA audio job unavailable','code':'AUDIO_ORIGINAL_MISSING','retryable':False})
        except (ValueError,OSError,RuntimeError,KeyError,URLError) as exc:
            from qa_audio_failures import safe_audio_error
            status, response = safe_audio_error(exc)
            return self.reply(status,response)"""

def patch(source: Path, target: Path) -> Path:
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != REVIEWED_SHA256:
        raise ValueError('QA source differs from reviewed version; no patch created')
    data = raw.decode('utf-8')
    if data.count(OLD) != 1:
        raise ValueError('QA audio handler not unique; no patch created')
    if data.count(TIMEOUT_OLD) != 1:
        raise ValueError('QA audio timeout handler differs; no patch created')
    data = data.replace(OLD,NEW,1).replace(TIMEOUT_OLD,TIMEOUT_NEW,1)
    compile(data,str(source),'exec')
    target.mkdir(parents=True,exist_ok=True)
    if source.resolve().is_relative_to(target.resolve()):
        raise ValueError('Refusing to patch the input in place')
    patched = target/'companion.py'
    patched.write_text(data)
    shutil.copyfile(Path(__file__).with_name('qa_audio_failures.py'),target/'qa_audio_failures.py')
    return patched

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: patch_qa.py SOURCE OUTPUT_DIRECTORY')
    print('QA_PATCH_PREPARED',patch(Path(sys.argv[1]),Path(sys.argv[2])))
