"""Create an immutable, SHA-pinned MAIN Owner logo overlay from reviewed base.

No service restart, migrations, data writes, or changes to JM/FER.
"""
from pathlib import Path
import hashlib
import os
import argparse
import shutil

# Strict source digest inventory protects unrelated MAIN Mixer, session and UI.
EXPECTED = {
    'web/montara.js': '7034fffd918c7213effbf0a9681f527d998f94b16104249886c1272d9b337a41',
    'urano/native_owner_browser_bridge.js': '85b799353b669a62d73ca71f629d491bda44aa418e96e4b6794fa2505cd71b63',
    'urano/native_owner_web_gateway.py': '7572f9a5b75585c1883063c24ea0fb61939ee3332036df2f00881f81b3fcb54e',
    'urano/native_owner_stage_http.py': 'd93cdc438db0216133a2ea690d3326afd0cdd98c931ef6b72bf09716df5cf565',
    'urano/native_owner_browser_surface.py': 'b87f21521ea53db217fc2e7c055065f9a41746e91b1af68c9e55563e8255c744',
    'main_project_name_wsgi.py': '9422252df5ac1ff30c67e465f46d36c260808bef20ac3967692d6cd0bb895cb5',
}
here = Path(__file__).parent
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--target',type=Path,required=True)
parser.add_argument('--test-only',action='store_true')
args=parser.parse_args()
src_base=args.source
dst=args.target
assert not dst.exists(), 'Never overwrite a deployed overlay'
if args.test_only:
    assert '/tmp/' in str(src_base.resolve()) and '/tmp/' in str(dst), 'Tests must stay in /tmp'
else:
    assert os.geteuid()==0, 'Production overlay must be root-owned'
    assert src_base.resolve()==Path('/opt/montara-main-release/main-jm-approved-mixer-20a201d')
    assert str(dst)=='/opt/montara-main-release/main-approved-logo-20261122'
for rel, digest in EXPECTED.items():
    actual=hashlib.sha256((src_base/rel).read_bytes()).hexdigest()
    if actual!=digest:
        raise RuntimeError(f'MAIN base file changed; fail closed: {rel}')
shutil.copytree(src_base,dst,symlinks=False)
# Some pinned read-only bundle assets have mode 0444; make only the fresh
# output files root-writable before applying reviewed replacements.
for artifact in dst.rglob('*'):
    if artifact.is_file():
        artifact.chmod(0o644)
def change(rel, old, new, n=1):
    p = dst/rel
    src = p.read_text()
    if src.count(old) != n:
        raise SystemExit(f"{rel} pattern expected {n}, got {src.count(old)}: {old[:100]}")
    p.write_text(src.replace(old,new, n if n>0 else -1))

# Replace only the proven logo widget, not the Music/Mixer/Companion/30-song code.
main_ui=(dst/'web/montara.js').read_text()
my_block=(here/'logo-widget.fragment.js').read_text()+'\n'
start='// ---------- branding ----------\n'
end='// ---------- continue: register the project, then cameras ----------\n'
assert main_ui.count(start)==1 and main_ui.count(end)==1
assert start not in my_block and end not in my_block
p=dst/'web/montara.js'
p.write_text(main_ui.split(start,1)[0] + start + my_block + end + main_ui.split(end,1)[1])

bridge='urano/native_owner_browser_bridge.js'
change(bridge, "'api/v1/wizard/upload','montara/uploads','montara/branding',",
      "'api/v1/wizard/upload','montara/uploads','montara/branding','montara/logo',")
change(bridge, """    if (p === '/montara/branding' && method === 'GET')
      return { kind:'metadata', data:{mode:'montara',has_logo:false} };
""", "")
change(bridge, """    const isStatus = operation === 'api/v1/wizard/status' &&""",
      """    if (operation==='montara/logo' &&
        !((method==='GET') || (method==='POST' && !address.search)))
      return {kind:'blocked'};
    const isStatus = operation === 'api/v1/wizard/status' &&""")
change(bridge, """    const audioQuery = audioRoute && params.size === 1 &&""",
      """    const logoQuery = operation==='montara/logo' && method==='GET' &&
      params.size===1 && /^[0-9]{1,16}$/.test(params.get('t')||'');
    const audioQuery = audioRoute && params.size === 1 &&""")
change(bridge, """    if (address.search && !isStatus && !review && !versionQuery && !audioQuery &&""",
      """    if (address.search && !logoQuery && !isStatus && !review && !versionQuery && !audioQuery &&""")

stage='urano/native_owner_stage_http.py'
change(stage,
      '''        ("GET","/api/v1/artifacts/sync"):"json",
        ("POST","/montara/branding"):"branding",''',
      '''        ("GET","/api/v1/artifacts/sync"):"json",
        ("GET","/montara/branding"):"json",
        ("POST","/montara/logo"):"logo-upload",
        ("POST","/montara/branding"):"branding",''')
change(stage,
      '''    if method=="GET" and path=="/api/v1/wizard/review":''',
      '''    if method=="GET" and path=="/montara/logo":
        if not query or re.fullmatch(r"t=[0-9]{1,16}",query):
            return NativeStageTarget(
                path + ("?" + query if query else ""),"review-media")
        return None
    if method=="GET" and path=="/api/v1/wizard/review":''')

gateway='urano/native_owner_web_gateway.py'
change(gateway,
      '''        elif kind=="upload-direct":''',
      '''        elif kind=="logo-upload":
            limit=10*1024*1024
            if (type(length) is not int or not 0 < length <= limit
                    or request.mimetype != "multipart/form-data"
                    or not request.mimetype_params.get("boundary")):
                return jsonify(error="A PNG, JPEG or WebP logo up to 10 MiB is required"),400
            request.max_content_length=limit
            body=request.stream
        elif kind=="upload-direct":''')

# The custom JS is statically SHA-pinned by the Main Owner; update only montara.js pin.
surface='urano/native_owner_browser_surface.py'
old_hash=hashlib.sha256((src_base/'web/montara.js').read_bytes()).hexdigest()
new_hash=hashlib.sha256((dst/'web/montara.js').read_bytes()).hexdigest()
change(surface,f'"montara.js": "{old_hash}"',f'"montara.js": "{new_hash}"')

# Main preflight keeps immutable MAIN bundle, session and Companion unchanged.
wrapper='main_project_name_wsgi.py'
main_old='/opt/montara-main-release/main-jm-approved-mixer-20a201d'
main_new='/opt/montara-main-release/main-approved-logo-20261122'
change(wrapper,f'_OVERLAY = Path("{main_old}")',f'_OVERLAY = Path("{main_new}")')
change(wrapper,
      '''             "urano/native_owner_web_gateway.py",
             "urano/native_owner_full_session_http.py",''',
      '''             "urano/native_owner_web_gateway.py",
             "urano/native_owner_stage_http.py",
             "urano/native_owner_full_session_http.py",''')
for rel in (bridge,gateway):
    origin=hashlib.sha256((src_base/rel).read_bytes()).hexdigest()
    updated=hashlib.sha256((dst/rel).read_bytes()).hexdigest()
    change(wrapper,f'"{origin}"',f'"{updated}"')
change(wrapper,
      '''    script = _OVERLAY / "web/full-session.js"''',
      '''    # Only the reviewed logo changes are allowed on MAIN.
    for relative, expected in (
        ("urano/native_owner_stage_http.py", "%s"),
        ("web/montara.js", "%s"),
        ("urano/native_owner_browser_surface.py", "%s"),
    ):
        file = _OVERLAY / relative
        if hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise RuntimeError("MAIN logo patch digest mismatch: " + relative)
    script = _OVERLAY / "web/full-session.js"''' % (
          hashlib.sha256((dst/stage).read_bytes()).hexdigest(),
          hashlib.sha256((dst/'web/montara.js').read_bytes()).hexdigest(),
          hashlib.sha256((dst/surface).read_bytes()).hexdigest(),
      ))
change(wrapper,
      '''from urano import (native_owner_browser_surface, native_owner_web_gateway,
                   native_owner_full_session_http, native_owner_mix_http,''',
      '''from urano import (native_owner_browser_surface, native_owner_web_gateway,
                   native_owner_stage_http,
                   native_owner_full_session_http, native_owner_mix_http,''')
change(wrapper,
      '''for module in (native_owner_browser_surface, native_owner_web_gateway,
               native_owner_full_session_http,''',
      '''for module in (native_owner_browser_surface, native_owner_web_gateway,
               native_owner_stage_http, native_owner_full_session_http,''')
for rel in [bridge,gateway,stage,surface,'web/montara.js',wrapper]:
    p=dst/rel
    print(rel,hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_size)

if not args.test_only:
    for item in dst.rglob('*'):
        if item.is_dir():item.chmod(0o755)
        if item.is_file():item.chmod(0o644)
    dst.chmod(0o755)
print('MAIN_LOGO_OVERLAY_CREATED',dst)
