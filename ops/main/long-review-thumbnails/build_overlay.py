"""Rebuild MAIN verified 305-shot thumbnails, preserving timeout/360/logo/Mixer.

Code only; pins every source file, refuses existing output and never deploys.
"""
from pathlib import Path
import argparse
import hashlib
import os
import shutil

BASE=Path("/opt/montara-main-release/main-review-timeout-20261123")
OUTPUT=Path("/opt/montara-main-release/main-reviewed-frames-20261123")
FRAG=Path(__file__).parent
PRECONDITIONS={
  "web/montara.js":"5d90a69eeab733312235238491a06a012a8e364e24a06adc3829a9d7fcf46aa5",
  "urano/native_owner_browser_bridge.js":"44b6147a880e5069e2eae5750296d844acc2e0fa31c98b4bafb37db516675f1c",
  "urano/native_owner_browser_surface.py":"81fee669fe6b026cdc9689a6ab9cc8859ec25099b6d023bb0acd30b2a9620d26",
  "main_project_name_wsgi.py":"38adb8b5f35cd988f0673321cc6db970eb707b234e7880df1e913eafc56021ea",
  "urano/native_owner_web_gateway.py":"0f98f51b3af3073dbf7e82015c3b1b8601991c89b20e58799e7138b667111ad3",
  "urano/native_owner_stage_http.py":"9ba12d659621167420fbbbdc81c85d7597d06f751127628f87964863770787a8",
}
RESULT={
  "web/montara.js":"a2d31ac28fb9d8b239788f7b7623468b0b08fd24b4f1d6272003563e22263a45",
  "urano/native_owner_browser_bridge.js":"0d6cbc48d2ced7ef3e92cda955a97d0968195b9b25f5f16bd1aea599b1890d00",
  "urano/native_owner_browser_surface.py":"14adc2eab1fa3ea9939edc8ed65d674a67f2598ec0fa0f84eb5bf492327ba217",
  "main_project_name_wsgi.py":"af471cd9335e5b3dc2e07d09631abed567f18d5bd4cbdad954605046cd0b567f",
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def replace(root,relative,old,new):
    file=root/relative
    text=file.read_text()
    if text.count(old)!=1:
        raise RuntimeError("Wrong reviewed anchor for: "+relative)
    file.write_text(text.replace(old,new,1))

def build(source,target,allow_scratch=False):
    if target.exists() or target.is_symlink():
        raise RuntimeError("Never replace a deployed code release")
    if allow_scratch:
        if not str(source.resolve()).startswith(("/tmp/","/private/tmp/")):
            raise RuntimeError("Scratch source must be under /tmp")
        if not str(target.resolve()).startswith(("/tmp/","/private/tmp/")):
            raise RuntimeError("Scratch target must be under /tmp")
    elif (os.geteuid()!=0 or source.resolve()!=BASE or target!=OUTPUT
          or source.is_symlink() or source.stat().st_uid!=0
          or source.stat().st_mode & 0o022):
        raise RuntimeError("Only immutable approved root-owned MAIN source")
    for rel,expected in PRECONDITIONS.items():
        if sha(source/rel)!=expected:
            raise RuntimeError("MAIN source changed; refuse "+rel)
    shutil.copytree(source,target,symlinks=False)
    for path in target.rglob("*"):
        if path.is_file():path.chmod(0o644)

    bridge="urano/native_owner_browser_bridge.js"
    replace(target,bridge,
        "              !selected.path.startsWith(nativePrefix+'api/v1/wizard/spherical-preview?')) {",
        "              !selected.path.startsWith(nativePrefix+'api/v1/wizard/spherical-preview?') &&\n"
        "              !selected.path.startsWith(nativePrefix+'api/v1/wizard/review/thumbnail/')) {")
    main="web/montara.js"
    replace(target,main,"let framesRequest=null;",
        (FRAG/"frame-thumb-observer.fragment.js").read_text()+"let framesRequest=null;")
    replace(target,main,
'''    if (item.thumbnail && img.getAttribute("src") !== item.thumbnail) {
      img.src = item.thumbnail;
      img.hidden = false;
      swapping.delete(item.index);
      fig.querySelector(".src").textContent = label;
''',
'''    if (item.thumbnail && img.dataset.reviewThumbnail !== item.thumbnail) {
      img.src=''; // Cancel prior Owner blob resolution before changing shot.
      img.dataset.reviewThumbnail=item.thumbnail;
      img.hidden = false;
      if(frameThumbObserver) frameThumbObserver.observe(img);
      else img.src=item.thumbnail;
      swapping.delete(item.index);
      fig.querySelector(".src").textContent = label;
''')
    surface="urano/native_owner_browser_surface.py"
    replace(target,surface,
        '"montara.js": "'+PRECONDITIONS[main]+'"',
        '"montara.js": "'+sha(target/main)+'"')
    wrapper="main_project_name_wsgi.py"
    replace(target,wrapper,
        '_OVERLAY = Path("/opt/montara-main-release/main-review-timeout-20261123")',
        '_OVERLAY = Path("/opt/montara-main-release/main-reviewed-frames-20261123")')
    for rel in (bridge,main,surface):
        replace(target,wrapper,PRECONDITIONS[rel],sha(target/rel))
    for rel,digest in RESULT.items():
        if sha(target/rel)!=digest:
            raise RuntimeError("Unreviewed output; refused "+rel)
        print("REPRODUCED",rel,digest)
    for rel in PRECONDITIONS:
        if rel not in RESULT and sha(target/rel)!=sha(source/rel):
            raise RuntimeError("Unrelated module was modified: "+rel)
    for path in target.rglob("*"):
        if path.is_dir():path.chmod(0o755)
        elif path.is_file():path.chmod(0o644)
    target.chmod(0o755)
    print("MAIN_305_THUMBNAIL_REVIEWED_BUILD_PASS",target)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--target",type=Path,required=True)
    p.add_argument("--test-only",action="store_true")
    args=p.parse_args()
    build(args.source,args.target,args.test_only)
