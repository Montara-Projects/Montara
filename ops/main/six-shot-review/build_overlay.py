"""Rebuild MAIN's six-editable-shot frontend without touching user data.

Source SHA pins, exact reviewed patch, output SHA pins, root-only production
paths. The builder does NOT restart a service or change any project/media.
"""
from pathlib import Path
import argparse,gzip,hashlib,os,shutil,subprocess

SOURCE=Path('/opt/montara-main-release/main-edit-save-20261123')
TARGET=Path('/opt/montara-main-release/main-six-editable-20261123')
BASE_PINS={
 'web/montara.js':'df0d77d8e6ac081f917ce32cb2973ae9489f79cedd6374e7af446e42e5953368',
 'urano/native_owner_browser_surface.py':'bdb2f8fa4b131abc676f834bb46066f8e9d4b59169d2e29dad8f5c932af034e0',
 'main_project_name_wsgi.py':'baae04c82f3744501824b344e5c3c78d8c032bad5ae9f74070130d00553e7626',
 'urano/native_owner_web_gateway.py':'5fea5c20022e0955a89d1e7cb82afae68435d8b58208bf4cf2b5cc2ab6adbcfb',
 'urano/native_owner_browser_bridge.js':'0d6cbc48d2ced7ef3e92cda955a97d0968195b9b25f5f16bd1aea599b1890d00',
 'urano/native_owner_stage_http.py':'9ba12d659621167420fbbbdc81c85d7597d06f751127628f87964863770787a8',
}
OUTPUT_PINS={
 'web/montara.js':'4c0e6add203d6b2fe5196a8009df86938ab16f1ca78fae5a63bf88aaddcdf314',
 'urano/native_owner_browser_surface.py':'b8b7d1dc243c3b1ab6546b4eaa0d8c38674a885e8a3005a9ca8154823a675d29',
 'main_project_name_wsgi.py':'854464097ee79e3687d02d410a112862628520fd5ab51034d3db3400ecfab4c8',
}
def sha(f):
 return hashlib.sha256(f.read_bytes()).hexdigest()

def build(source,dest,test_only=False):
 if dest.exists() or dest.is_symlink():
  raise RuntimeError('Refuse to overwrite existing release')
 if test_only:
  if (not str(source.resolve()).startswith(('/tmp/','/private/tmp/'))
      or not str(dest.resolve()).startswith(('/tmp/','/private/tmp/'))):
   raise RuntimeError('Scratch tests must be under tmp')
 elif (os.geteuid()!=0 or source.resolve()!=SOURCE or dest!=TARGET or
       source.is_symlink() or source.stat().st_uid!=0 or source.stat().st_mode & 0o022):
  raise RuntimeError('Expected root-owned immutable MAIN source')
 for rel,expected in BASE_PINS.items():
  if sha(source/rel)!=expected:raise RuntimeError('Unexpected source digest '+rel)
 shutil.copytree(source,dest,symlinks=False)
 for file in dest.rglob('*'):
  if file.is_file():file.chmod(0o644)
 try:
  diff=gzip.decompress(Path(__file__).with_name('main-six-editable.patch.gz').read_bytes())
  subprocess.run(['patch','-p0','--batch','--forward','--fuzz=0','--reject-file=-'],
    cwd=dest,input=diff,capture_output=True,check=True,timeout=15)
  for rel,expected in OUTPUT_PINS.items():
   if sha(dest/rel)!=expected:raise RuntimeError('Wrong output digest '+rel)
  for rel,expected in BASE_PINS.items():
   if rel not in OUTPUT_PINS and sha(dest/rel)!=expected:
    raise RuntimeError('Unrelated code changed '+rel)
  for file in dest.rglob('*'):
   if file.is_dir():file.chmod(0o755)
   elif file.is_file():file.chmod(0o644)
  dest.chmod(0o755)
 except BaseException:
  shutil.rmtree(dest)
  raise
 print('MAIN_SIX_EDITABLE_BUILD_REPRODUCED_VERIFIED_CANDIDATE',dest)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--source',required=True,type=Path)
 p.add_argument('--target',required=True,type=Path)
 p.add_argument('--test-only',action='store_true')
 a=p.parse_args()
 build(a.source,a.target,a.test_only)
