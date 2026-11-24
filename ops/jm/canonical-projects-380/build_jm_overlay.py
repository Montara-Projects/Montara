"""Stage (never activate) #380 Owner JS over pinned LAB-JM portal overlay."""
from __future__ import annotations
import argparse
import hashlib
import shutil
from pathlib import Path

SOURCE=Path('/opt/montara/jmlab-mixer-label-hotfix-20261122')
PINNED_WEB='0ea9c8794591564565a716bb99a9791624fabf47093f05751aab9e3d2662680a'
PINNED_SURFACE='fc0fe9eac256cb550d3e172bf1da687ea4fcba927ef66195350a4d3ada40b0d1'
PINNED_WSGI='32b619676bd30966cef191cf2f96f65b1cf4ad965fb084e4c5fa789b0170216c'


def digest(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def replace_one(text:str,needle:str,replacement:str)->str:
    if text.count(needle)!=1:raise RuntimeError(f'Expected exactly one reviewed pin for {needle[:32]}')
    return text.replace(needle,replacement)

def build(*,dest:Path,reviewed:Path):
    if not str(dest).startswith('/opt/montara/jmlab-canonical-380-') or dest.exists():
        raise RuntimeError('Refuse to overwrite Owner portal or unknown path')
    for name,sha in [('web/montara.js',PINNED_WEB),('urano/native_owner_browser_surface.py',PINNED_SURFACE),('jmlab_ui_performance_wsgi.py',PINNED_WSGI)]:
        if digest(SOURCE/name)!=sha:raise RuntimeError('JM live source drift: '+name)
    if SOURCE.is_symlink() or SOURCE.stat().st_uid != 0:
        raise RuntimeError('Untrusted source overlay')
    if not reviewed.is_file() or reviewed.is_symlink():raise RuntimeError('Missing reviewed JS')
    shutil.copytree(SOURCE,dest)
    shutil.copyfile(reviewed,dest/'web/montara.js')
    surface=dest/'urano/native_owner_browser_surface.py'
    surface.write_text(replace_one(surface.read_text(),PINNED_WEB,digest(dest/'web/montara.js')))
    wsgi=dest/'jmlab_ui_performance_wsgi.py';w=wsgi.read_text()
    w=replace_one(w,str(SOURCE),str(dest))
    w=replace_one(w,PINNED_WEB,digest(dest/'web/montara.js'))
    w=replace_one(w,PINNED_SURFACE,digest(surface))
    wsgi.write_text(w)
    for p in dest.rglob('*'):
        if p.is_dir():p.chmod(0o755)
        if p.is_file():p.chmod(0o644)
    dest.chmod(0o755)
    assert digest(SOURCE/'web/full-session.js')==digest(dest/'web/full-session.js')
    assert digest(SOURCE/'urano/native_owner_web_gateway.py')==digest(dest/'urano/native_owner_web_gateway.py')
    print('CANONICAL_380_OVERLAY_STAGED_NOT_LIVE',dest,digest(dest/'web/montara.js'))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--dest',type=Path,required=True)
    parser.add_argument('--reviewed',type=Path,required=True)
    v=parser.parse_args();build(dest=v.dest,reviewed=v.reviewed)
