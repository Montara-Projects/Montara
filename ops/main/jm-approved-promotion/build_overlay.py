"""Fail-closed MAIN-isolated Owner release: preserve existing MAIN assets and routes.

Run on authorized VM as root. Never operate on LAB-JM, FER, betamain, or R2.
No service restart, no media mutations. Output is a new immutable directory.
"""
from pathlib import Path
import argparse
import hashlib
import shutil

BASE = Path('/opt/montara-main-release/main-project-name-overlay-20261121')
EXPECTED = {
    'web/montara.js':'620a8b270f4d8e023f7ff612d879968b5fd54e6e468b3cc93fb8ca23449c5909',
    'web/track-types.js':'eef3fcd4bf2685bc15634670c3b36271c00b04cb3b2fab0bcc5fcc7d2f797626',
    'urano/native_owner_browser_bridge.js':'408bd50a661c5848f6e1ccb5348840b5f2f358766ca1448cf7a929149215115a',
}

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def one(s,old,new,label):
    n=s.count(old)
    if n!=1:raise RuntimeError(f'{label}: expected one match, got {n}')
    return s.replace(old,new)

def build(src,dst,fragments,bundle):
    assert src.is_dir() and src.resolve()==BASE.resolve() and not src.is_symlink()
    assert not dst.exists() and str(dst).startswith('/opt/montara-main-release/')
    for rel,expected in EXPECTED.items():
        if digest(src/rel)!=expected:raise RuntimeError(f'MAIN file changed: {rel}')
    shutil.copytree(src,dst,symlinks=False)
    types=dst/'web/track-types.js'; s=types.read_text()
    s=one(s,"['vocal', 'Lead vocal'], ['backing_vocal', 'Backing vocal'],","['vocal', 'Lead vocal'], ['co_lead_vocal', 'Co-lead vocal'], ['backing_vocal', 'Backing vocal'], ['choir', 'Choir / group vocals'],",'voice choices')
    s=one(s,"    backing_vocal: ['backing', 'bv', 'bvs', 'choir', 'coros', 'harmony'],", "    co_lead_vocal: ['co-lead', 'co lead', 'colead', 'duet vocal', 'duo vocal'],\n    choir: ['choir', 'chorus voices', 'choir vocals', 'coro', 'coros'],\n    backing_vocal: ['backing', 'bv', 'bvs', 'harmony'],",'voice synonyms')
    s=one(s,"'podcast_voice', 'narration', 'backing_vocal', 'vocal', 'room'","'podcast_voice', 'narration', 'co_lead_vocal', 'choir', 'backing_vocal', 'vocal', 'room'",'voice guess order')
    # Deliberately preserve MAIN's advanced, filename-cleaning sourceLabel implementation.
    assert 'sourceLabel, of, set, forFiles, controls, label: labelOf' in s
    types.write_text(s)

    ui=dst/'web/montara.js'; s=ui.read_text()
    s=one(s,"['vocal','backing_vocal','podcast_voice','narration']","['vocal','co_lead_vocal','backing_vocal','choir','podcast_voice','narration']",'MAIN channel voice family')
    s=one(s,"['vocal','backing_vocal'].includes(kind)","['vocal','co_lead_vocal','backing_vocal','choir'].includes(kind)",'MAIN channel short labels')
    ui.write_text(s)

    bridge=dst/'urano/native_owner_browser_bridge.js';s=bridge.read_text()
    before="        const item = document.createElement('li');\n        item.textContent = name;\n        list.append(item);"
    after=(fragments/'owner_buttons.fragment').read_text().rstrip('\n')
    s=one(s,before,after,'MAIN project open/delete')
    bridge.write_text(s)
    css=dst/'urano/owner_account.css'; css.write_text(css.read_text()+'\n'+(fragments/'owner_buttons.css').read_text())

    surf=dst/'urano/native_owner_browser_surface.py'; s=surf.read_text()
    for asset in ('montara.js','track-types.js'):
        old=EXPECTED[f'web/{asset}'];new=digest(dst/'web'/asset)
        s=one(s,f'"{asset}": "{old}"',f'"{asset}": "{new}"',f'asset digest {asset}')
    surf.write_text(s)

    wsgi=dst/'main_project_name_wsgi.py';s=wsgi.read_text()
    s=one(s,str(src),str(dst),'MAIN overlay path')
    s=one(s,'/opt/montara/bundles/jm-61a57fd9ad46df4a8cfc0ae9c3b270b28119e009',str(bundle),'MAIN approved backend bundle')
    s=one(s,EXPECTED['urano/native_owner_browser_bridge.js'],digest(bridge),'bridge SHA')
    wsgi.write_text(s)
    for p in dst.rglob('*'):
        if p.is_dir():p.chmod(0o755)
        if p.is_file():p.chmod(0o644)
    dst.chmod(0o755)
    print('STAGED',dst)
    for rel in ('web/montara.js','web/track-types.js','urano/native_owner_browser_bridge.js','urano/native_owner_browser_surface.py'):
        print('SHA256',rel,digest(dst/rel))
    print('PRESERVED_MAIN_FULL_SESSION',digest(src/'web/full-session.js')==digest(dst/'web/full-session.js'))
    print('PRESERVED_MAIN_GATEWAY',digest(src/'urano/native_owner_web_gateway.py')==digest(dst/'urano/native_owner_web_gateway.py'))
    # MAIN's companion.js is supplied by the signed underlying bundle, not every overlay.
    if (src/'web/companion.js').exists():
        print('PRESERVED_MAIN_COMPANION',digest(src/'web/companion.js')==digest(dst/'web/companion.js'))
    else:
        print('PRESERVED_MAIN_COMPANION', 'bundled upstream — no overlay copy')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--target',type=Path,required=True);ap.add_argument('--fragments',type=Path,required=True);ap.add_argument('--bundle',type=Path,required=True)
    a=ap.parse_args();build(BASE,a.target,a.fragments,a.bundle)
