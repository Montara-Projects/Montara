"""Stage reviewed #379 assets over currently-live JM Owner portal, never activate.

Requires exact immutable source digests. All output is a new root-owned overlay,
so a failure cannot modify the original portal, broker, any sessions or media.
"""
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path
import argparse

SOURCE = Path('/opt/montara/jmlab-mixer-label-hotfix-20261122')
SOURCES = {
    'urano/native_owner_browser_bridge.js':'412bbd4c0fd98e36da98c449174b850c83da825503c0fcfc456c5520fb186db7',
    'urano/native_owner_mix_http.py':'09fd943d007b3e10e7b48083a40ad056c558894bd663759a7dd09ad6b86aecac',
    'urano/native_owner_browser_surface.py':'fc0fe9eac256cb550d3e172bf1da687ea4fcba927ef66195350a4d3ada40b0d1',
    'jmlab_ui_performance_wsgi.py':'32b619676bd30966cef191cf2f96f65b1cf4ad965fb084e4c5fa789b0170216c',
    'web/montara.js':'0ea9c8794591564565a716bb99a9791624fabf47093f05751aab9e3d2662680a',
}


def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()

def one(value:str,old:str,new:str,label:str)->str:
    if value.count(old)!=1:raise ValueError(f'{label} expected one pinned occurrence; found {value.count(old)}')
    return value.replace(old,new)

def stage(dest:Path,reviewed:Path):
    if SOURCE.is_symlink() or not SOURCE.is_dir() or SOURCE.stat().st_uid!=0:
        raise RuntimeError('Missing reviewed JM source overlay')
    if dest.exists() or not str(dest).startswith('/opt/montara/jmlab-audio-projects-379-'):
        raise RuntimeError('Refusing overwrite of existing JM overlay')
    for item,digest in SOURCES.items():
        if sha(SOURCE/item)!=digest:raise RuntimeError(f'JM overlay drift: {item}')
    for item in ('native_owner_browser_bridge.js','native_owner_mix_http.py','active_web_montara.js'):
        if not (reviewed/item).is_file():raise RuntimeError(f'Missing reviewed source: {item}')
    shutil.copytree(SOURCE,dest,symlinks=False)
    for source,target in [('native_owner_browser_bridge.js','urano/native_owner_browser_bridge.js'),
                          ('native_owner_mix_http.py','urano/native_owner_mix_http.py'),
                          ('active_web_montara.js','web/montara.js')]:
        shutil.copyfile(reviewed/source,dest/target)
    # The source asset digests and Owner WSGI digest are all re-pinned together.
    surf=dest/'urano/native_owner_browser_surface.py'
    surf.write_text(one(surf.read_text(),SOURCES['web/montara.js'],sha(dest/'web/montara.js'),'JS digest in surface'))
    wsgi=dest/'jmlab_ui_performance_wsgi.py';s=wsgi.read_text()
    s=one(s,str(SOURCE),str(dest),'reviewed JM overlay directory')
    s=one(s,SOURCES['urano/native_owner_browser_bridge.js'],sha(dest/'urano/native_owner_browser_bridge.js'),'Owner private bridge digest')
    s=one(s,SOURCES['web/montara.js'],sha(dest/'web/montara.js'),'Owner web script digest')
    s=one(s,SOURCES['urano/native_owner_browser_surface.py'],sha(surf),'Owner surface digest')
    s=one(s,'("web/montara.js", "'+sha(dest/'web/montara.js')+'"),',
        '("web/montara.js", "'+sha(dest/'web/montara.js')+'"),\n            ("urano/native_owner_mix_http.py", "'+sha(dest/'urano/native_owner_mix_http.py')+'"),',
        'add strict Mix project RPC digest')
    wsgi.write_text(s)
    # The base Owner overlay carries an asset manifest. Recompute it AFTER
    # applying the reviewed #379 patches so it never describes stale bytes.
    manifest_path = dest / 'integrity.json'
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict) or not manifest:
        raise RuntimeError('Invalid copied integrity manifest')
    for relative, expected in manifest.items():
        asset = dest / relative
        if (not isinstance(relative, str) or not isinstance(expected, str)
                or not asset.is_file() or asset.is_symlink()
                or asset.resolve().is_relative_to(dest.resolve()) is False):
            raise RuntimeError('Missing or untrusted integrity asset: ' + str(relative))
        manifest[relative] = sha(asset)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    if any(sha(dest / relative) != digest for relative, digest in manifest.items()):
        raise RuntimeError('Stage asset integrity check failed')
    for p in dest.rglob('*'):
        if p.is_dir():p.chmod(0o755)
        if p.is_file():p.chmod(0o644)
    dest.chmod(0o755)
    print('JM_AUDIO_OVERLAY_STAGED_ONLY',dest)
    for item in ('web/montara.js','urano/native_owner_browser_bridge.js','urano/native_owner_mix_http.py','urano/native_owner_browser_surface.py'):
        print('SHA256',item,sha(dest/item))
    print('PRESERVED_JM_SESSION',sha(SOURCE/'web/full-session.js')==sha(dest/'web/full-session.js'))
    print('PRESERVED_JM_GATEWAY',sha(SOURCE/'urano/native_owner_web_gateway.py')==sha(dest/'urano/native_owner_web_gateway.py'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dest',required=True,type=Path);p.add_argument('--reviewed',required=True,type=Path)
    a=p.parse_args();stage(a.dest,a.reviewed)
