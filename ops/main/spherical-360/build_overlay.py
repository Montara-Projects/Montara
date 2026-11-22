"""Port only approved JM 360 preview routes to MAIN's logo-approved release.

Fails closed if the pinned MAIN source differs. Creates an immutable new
overlay without service restart, user project writes or Engine/broker changes.
"""
from __future__ import annotations
import argparse
import hashlib
import os
import shutil
from pathlib import Path

BASE=Path('/opt/montara-main-release/main-approved-logo-20261122')
TARGET=Path('/opt/montara-main-release/main-approved-360-20261122')
PRECONDITIONS={
    'urano/native_owner_browser_bridge.js':'fba37d11e16550c3817491e9c5101179f034cbc796d675a5d34c89059a0d0529',
    'urano/native_owner_stage_http.py':'18a4faba2d034506d34458386e72febf2286e1af1097b13f40be4370d344d0a3',
    'main_project_name_wsgi.py':'2bb18c5fde7c6659c482a34c561e0cacd8a7be7d604df0cdba096c03cfda1bab',
    'web/montara.js':'5d90a69eeab733312235238491a06a012a8e364e24a06adc3829a9d7fcf46aa5',
    'urano/native_owner_web_gateway.py':'d1f57221c331d838943511dd2f960214da974cb475abe23af2dd86606f084c35',
    'urano/native_owner_browser_surface.py':'81fee669fe6b026cdc9689a6ab9cc8859ec25099b6d023bb0acd30b2a9620d26',
}
FRAG=Path(__file__).parent

def sha(p:Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def one(root:Path,relative:str,old:str,new:str):
    file=root/relative
    s=file.read_text()
    if s.count(old)!=1:
        raise RuntimeError(f'Unsafe MAIN spherical patch: {relative}: expected exactly one anchor; got {s.count(old)}')
    file.write_text(s.replace(old,new,1))

def build(source:Path,target:Path,*,test_only:bool=False):
    if target.exists() or target.is_symlink():
        raise RuntimeError('Refusing to overwrite an existing MAIN release')
    if test_only:
        if '/tmp/' not in str(source.resolve()) or '/tmp/' not in str(target):
            raise RuntimeError('Test source and target must both be in /tmp')
    else:
        if os.geteuid()!=0 or source.resolve()!=BASE or target!=TARGET:
            raise RuntimeError('Only fixed, root-owned MAIN paths are allowed')
        if source.is_symlink() or source.stat().st_uid!=0 or source.stat().st_mode & 0o022:
            raise RuntimeError('MAIN source cannot be writable by untrusted users')
    for rel,expected in PRECONDITIONS.items():
        if sha(source/rel)!=expected:
            raise RuntimeError('Unreviewed MAIN source changed: '+rel)
    shutil.copytree(source,target,symlinks=False)
    for artifact in target.rglob('*'):
        if artifact.is_file():
            artifact.chmod(0o644)
    bridge='urano/native_owner_browser_bridge.js'
    one(target,bridge,"    'api/v1/wizard/cancel', 'api/v1/wizard/status',\n",
        "    'api/v1/wizard/cancel', 'api/v1/wizard/status',\n"
        "    'api/v1/wizard/spherical-source-frame', 'api/v1/wizard/spherical-preview',\n")
    one(target,bridge,
        "    const params = address.searchParams;\n    if (operation==='montara/logo'",
        "    const params = address.searchParams;\n"+
        (FRAG/'owner-spherical.fragment.js').read_text()+
        "    if (operation==='montara/logo'")
    one(target,bridge,
        "    if (address.search && !logoQuery && !isStatus",
        "    if (address.search && !sphericalQuery && !spherePreview && !logoQuery && !isStatus")
    one(target,bridge,
        "              !selected.path.startsWith(nativePrefix+'api/v1/edit/shot/frame?')) {",
        "              !selected.path.startsWith(nativePrefix+'api/v1/edit/shot/frame?') &&\n"
        "              !selected.path.startsWith(nativePrefix+'api/v1/wizard/spherical-preview?')) {")
    stage='urano/native_owner_stage_http.py'
    one(target,stage,'_MAX_QUERY = 2048\n',
        '_MAX_QUERY = 2048\n'+(FRAG/'stage-source-regex.fragment.py').read_text()+'\n')
    one(target,stage,'    if path.startswith("/api/v1/settings/"):\n',
        (FRAG/'stage-route.fragment.py').read_text()+
        '    if path.startswith("/api/v1/settings/"):\n')
    wsgi='main_project_name_wsgi.py'
    one(target,wsgi,
        '_OVERLAY = Path("/opt/montara-main-release/main-approved-logo-20261122")',
        '_OVERLAY = Path("/opt/montara-main-release/main-approved-360-20261122")')
    one(target,wsgi,PRECONDITIONS[bridge],sha(target/bridge))
    one(target,wsgi,PRECONDITIONS[stage],sha(target/stage))
    for rel in ('web/montara.js','urano/native_owner_web_gateway.py',
                'urano/native_owner_browser_surface.py'):
        if sha(source/rel)!=sha(target/rel):
            raise RuntimeError('Unreviewed MAIN component modified: '+rel)
    for artifact in target.rglob('*'):
        if artifact.is_dir():artifact.chmod(0o755)
        elif artifact.is_file():artifact.chmod(0o644)
    target.chmod(0o755)
    print('MAIN_360_IMMUTABLE_OVERLAY_CREATED',target)
    for rel in (bridge,stage,wsgi):
        print('MAIN_360_SHA256',rel,sha(target/rel))
    print('PRESERVED_LOGO_MIXER_COMPANION_MAIN_ASSETS')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--target',type=Path,required=True)
    parser.add_argument('--test-only',action='store_true')
    a=parser.parse_args()
    build(a.source,a.target,test_only=a.test_only)
