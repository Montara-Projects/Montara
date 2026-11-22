"""Reproduce the targeted MAIN Stage-review timeout fix, preserving #389/#390.

Build-only: no media access, no service changes, fail-closed on source drift.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
from pathlib import Path

BASE=Path('/opt/montara-main-release/main-approved-360-20261122')
OUTPUT=Path('/opt/montara-main-release/main-review-timeout-20261123')
EXPECTED={
    'urano/native_owner_web_gateway.py': 'd1f57221c331d838943511dd2f960214da974cb475abe23af2dd86606f084c35',
    'main_project_name_wsgi.py': '432813519821f84c789763d7daf747ce52b0e9b9fea8250b59491b4a95cf6546',
    'urano/native_owner_browser_bridge.js': '44b6147a880e5069e2eae5750296d844acc2e0fa31c98b4bafb37db516675f1c',
    'urano/native_owner_stage_http.py': '9ba12d659621167420fbbbdc81c85d7597d06f751127628f87964863770787a8',
    'web/montara.js': '5d90a69eeab733312235238491a06a012a8e364e24a06adc3829a9d7fcf46aa5',
}
EXPECTED_OUTPUT={
    'urano/native_owner_web_gateway.py': '0f98f51b3af3073dbf7e82015c3b1b8601991c89b20e58799e7138b667111ad3',
    'main_project_name_wsgi.py': '38adb8b5f35cd988f0673321cc6db970eb707b234e7880df1e913eafc56021ea',
}

def digest(p: Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def substitute(root:Path, rel:str, old:str, new:str):
    file=root/rel
    source=file.read_text()
    if source.count(old)!=1:
        raise RuntimeError(f'Unreviewed source in {rel}, anchor count={source.count(old)}')
    file.write_text(source.replace(old,new,1))

def build(src:Path,dst:Path,test_only:bool):
    if dst.exists() or dst.is_symlink():
        raise RuntimeError('Never overwrite a MAIN release')
    if test_only:
        if not str(src.resolve()).startswith(('/tmp/','/private/tmp/')) or not str(dst.resolve()).startswith(('/tmp/','/private/tmp/')):
            raise RuntimeError('Scratch verification must remain in /tmp')
    elif (os.geteuid()!=0 or src.resolve()!=BASE or dst!=OUTPUT or
          src.is_symlink() or src.stat().st_uid!=0 or src.stat().st_mode & 0o022):
        raise RuntimeError('Expected immutable root-owned MAIN 360 source only')
    for rel,sha in EXPECTED.items():
        if digest(src/rel)!=sha:
            raise RuntimeError('Reviewed MAIN 360 base has drifted: '+rel)
    shutil.copytree(src,dst,symlinks=False)
    for artifact in dst.rglob('*'):
        if artifact.is_file():artifact.chmod(0o644)
    gateway='urano/native_owner_web_gateway.py'
    substitute(dst,gateway,'_MAX_CHUNK = 16 * 1024 * 1024\n',
'''_MAX_CHUNK = 16 * 1024 * 1024


def _review_read_timeout(method: str, path: str, query: str) -> float | None:
    """Bounded Stage review wait AFTER per-owner authentication and socket grant.

    The Editor starts at "Preparing your shots" then GETs
    /wizard/review?render=1. Real worker answered HTTP 200 after 7.64s on
    MAIN, while Owner's default socket timeout (~6s) returned 503.
    This is an exact allowlist; never extend arbitrary control-plane RPCs.
    """
    if (method == "GET" and path == "/api/v1/wizard/review"
            and re.fullmatch(r"render=[01](?:&shot=[0-9]{1,5})?", query)):
        return 95.0
    return None
''')
    substitute(dst,gateway,'                headers={"Cache-Control":"no-store"}\n',
'''                # Authenticated, worker-generation-bound socket already granted.
                # Never widen global broker or other JSON request timeouts.
                review_wait = _review_read_timeout(
                    upstream_method, upstream_path, query)
                if review_wait is not None:
                    conn.timeout = review_wait
                    if conn.sock is not None:
                        conn.sock.settimeout(review_wait)
                headers={"Cache-Control":"no-store"}
''')
    wrapper='main_project_name_wsgi.py'
    substitute(dst,wrapper,
        '_OVERLAY = Path("/opt/montara-main-release/main-approved-360-20261122")',
        '_OVERLAY = Path("/opt/montara-main-release/main-review-timeout-20261123")')
    substitute(dst,wrapper,EXPECTED[gateway],digest(dst/gateway))
    for rel,sha in EXPECTED_OUTPUT.items():
        if digest(dst/rel)!=sha:
            raise RuntimeError('Unexpected candidate hash, fail closed: '+rel)
    for rel in EXPECTED:
        if rel not in EXPECTED_OUTPUT and digest(src/rel)!=digest(dst/rel):
            raise RuntimeError('Unrelated MAIN functionality was modified: '+rel)
    for artifact in dst.rglob('*'):
        if artifact.is_dir(): artifact.chmod(0o755)
        elif artifact.is_file(): artifact.chmod(0o644)
    dst.chmod(0o755)
    print('MAIN_REVIEW_TIMEOUT_OVERLAY_CREATED',dst)
    print('MAIN_REVIEW_TIMEOUT_GATEWAY_SHA',digest(dst/gateway))
    print('MAIN_REVIEW_TIMEOUT_WSGI_SHA',digest(dst/wrapper))
    print('MAIN_360_LOGO_MIXER_SESSION_COMPANION_PRESERVED')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True,type=Path)
    p.add_argument('--target',required=True,type=Path)
    p.add_argument('--test-only',action='store_true')
    a=p.parse_args()
    build(a.source,a.target,a.test_only)
