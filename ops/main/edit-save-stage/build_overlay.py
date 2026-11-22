"""Apply the reviewed, strictly SHA-pinned MAIN Edit/Save Shot overlay patch.

The script only creates a new code-only target. No service restart, file
migration, media write or in-flight request changes. It fails closed on
unexpected source file digests or output patch mismatch.
"""
import argparse
import hashlib
import gzip
import os
from pathlib import Path
import shutil
import subprocess

BASE=Path('/opt/montara-main-release/main-reviewed-frames-20261123')
TARGET=Path('/opt/montara-main-release/main-edit-save-20261123')
PIN={
    'urano/native_owner_web_gateway.py':'0f98f51b3af3073dbf7e82015c3b1b8601991c89b20e58799e7138b667111ad3',
    'urano/native_owner_browser_surface.py':'14adc2eab1fa3ea9939edc8ed65d674a67f2598ec0fa0f84eb5bf492327ba217',
    'web/montara.js':'a2d31ac28fb9d8b239788f7b7623468b0b08fd24b4f1d6272003563e22263a45',
    'main_project_name_wsgi.py':'af471cd9335e5b3dc2e07d09631abed567f18d5bd4cbdad954605046cd0b567f',
    'urano/native_owner_browser_bridge.js':'0d6cbc48d2ced7ef3e92cda955a97d0968195b9b25f5f16bd1aea599b1890d00',
    'urano/native_owner_stage_http.py':'9ba12d659621167420fbbbdc81c85d7597d06f751127628f87964863770787a8',
}
RESULT={
    'urano/native_owner_web_gateway.py':'5fea5c20022e0955a89d1e7cb82afae68435d8b58208bf4cf2b5cc2ab6adbcfb',
    'urano/native_owner_browser_surface.py':'bdb2f8fa4b131abc676f834bb46066f8e9d4b59169d2e29dad8f5c932af034e0',
    'web/montara.js':'df0d77d8e6ac081f917ce32cb2973ae9489f79cedd6374e7af446e42e5953368',
    'main_project_name_wsgi.py':'baae04c82f3744501824b344e5c3c78d8c032bad5ae9f74070130d00553e7626',
}

def digest(file: Path)->str:
    return hashlib.sha256(file.read_bytes()).hexdigest()

def build(source:Path,target:Path,scratch:bool):
    if target.exists() or target.is_symlink():
        raise RuntimeError('Never overwrite an existing MAIN code release')
    if scratch:
        if not str(source.resolve()).startswith(('/tmp/','/private/tmp/')):
            raise RuntimeError('Scratch source must be under /tmp')
        if not str(target.resolve()).startswith(('/tmp/','/private/tmp/')):
            raise RuntimeError('Scratch destination must be under /tmp')
    elif (os.geteuid()!=0 or source.resolve()!=BASE or target!=TARGET or
          source.is_symlink() or source.stat().st_uid!=0 or source.stat().st_mode & 0o022):
        raise RuntimeError('Expected root-owned immutable MAIN release only')
    for rel,expected in PIN.items():
        if digest(source/rel)!=expected:
            raise RuntimeError('Unreviewed source file: '+rel)
    shutil.copytree(source,target,symlinks=False)
    for artifact in target.rglob('*'):
        if artifact.is_file(): artifact.chmod(0o644)
    packed=Path(__file__).with_name('reviewed-main-edit-save.patch.gz')
    reviewed_diff=gzip.decompress(packed.read_bytes())
    try:
        subprocess.run(['patch','-p0','--batch','--forward','--fuzz=0',
                        '--reject-file=-'],
                       input=reviewed_diff,cwd=target,check=True,
                       capture_output=True,timeout=15)
        for rel,expected in RESULT.items():
            if digest(target/rel)!=expected:
                raise RuntimeError('Output differs from reviewed MAIN candidate: '+rel)
        for rel,expected in PIN.items():
            if rel not in RESULT and digest(target/rel)!=expected:
                raise RuntimeError('Unrelated MAIN module changed: '+rel)
        for artifact in target.rglob('*'):
            if artifact.is_dir():artifact.chmod(0o755)
            elif artifact.is_file():artifact.chmod(0o644)
        target.chmod(0o755)
    except BaseException:
        # If a source or patch mismatch occurs, never leave an apparently
        # deployable, partially patched directory.
        shutil.rmtree(target)
        raise
    print('MAIN_EDIT_SAVE_OUTPUT_MATCHES_LIVE_REVIEWED_CANDIDATE')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--target',type=Path,required=True)
    parser.add_argument('--test-only',action='store_true')
    args=parser.parse_args()
    build(args.source,args.target,args.test_only)
