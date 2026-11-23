"""Build a *new* LAB-JM Stage #359 overlay on the approved Audio #379 overlay.

Source directories must be immutable, root-owned copies already reviewed on the VM.
This builder DOES NOT modify systemd, start services or touch Owner media/data.
The Engine must stay pinned separately; this only reconciles Owner/UI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


FILES = (
    "web/montara.js",
    "urano/native_owner_browser_bridge.js",
    "urano/native_owner_web_gateway.py",
)
CUT = "web/cut-editor.js"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_one(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one pinned occurrence, got {count}")
    return source.replace(old, new)


def checked_tree(path: Path) -> Path:
    if not path.is_dir() or path.is_symlink():
        raise ValueError(f"Not a trusted immutable tree: {path}")
    if path.stat().st_uid != 0 or path.stat().st_mode & 0o022:
        raise ValueError(f"Untrusted root-owned tree: {path}")
    return path


def build(live: Path, base: Path, stage: Path, dest: Path) -> None:
    live, base, stage = (checked_tree(p) for p in (live, base, stage))
    if dest.exists() or dest.is_symlink() or not str(dest).startswith(
        "/opt/montara/jmlab-stage359-on-audio379-"
    ):
        raise ValueError("Refusing overwrite or non-JM destination")
    old_integrity = json.loads((live / "integrity.json").read_text())
    if not isinstance(old_integrity, dict) or not old_integrity:
        raise ValueError("Missing #379 integrity manifest")
    if any(digest(live / key) != value for key, value in old_integrity.items()):
        raise ValueError("#379 baseline integrity failed")
    if b"/montara/mix/projects" not in (live / "web/montara.js").read_bytes():
        raise ValueError("Current source lacks approved Audio #379")

    shutil.copytree(live, dest, symlinks=False)
    changes: dict[str, str] = {}
    for name in FILES:
        result = subprocess.run(
            ["git", "merge-file", "-p", str(live / name),
             str(base / name), str(stage / name)],
            capture_output=True,
            check=False,
        )
        if result.returncode or b"<<<<<<<" in result.stdout:
            raise ValueError(f"Three-way merge failed: {name}")
        (dest / name).write_bytes(result.stdout)
        changes[name] = digest(dest / name)

    shutil.copyfile(stage / CUT, dest / CUT)
    changes[CUT] = digest(dest / CUT)

    surface = dest / "urano/native_owner_browser_surface.py"
    text = require_one(
        surface.read_text(), digest(live / "web/montara.js"),
        changes["web/montara.js"], "Surface JS digest"
    )
    matcher = re.search(r'(?m)^(\s*)"montara.js": "[a-f0-9]{64}",$', text)
    if matcher is None:
        raise ValueError("Surface allowlist anchor missing")
    text = (
        text[:matcher.end()]
        + "\n" + matcher.group(1) + '"cut-editor.js": "' + changes[CUT] + '",'
        + text[matcher.end():]
    )
    surface.write_text(text)
    changes["urano/native_owner_browser_surface.py"] = digest(surface)

    wsgi = dest / "jmlab_ui_performance_wsgi.py"
    text = require_one(wsgi.read_text(), str(live), str(dest), "Overlay path")
    for name in (
        "web/montara.js",
        "urano/native_owner_browser_bridge.js",
        "urano/native_owner_browser_surface.py",
        "urano/native_owner_web_gateway.py",
    ):
        text = require_one(
            text, digest(live / name), changes[name], f"WSGI digest {name}"
        )
    text = require_one(
        text, '"web/montara.js", "web/track-types.js"',
        '"web/montara.js", "web/cut-editor.js", "web/track-types.js"',
        "WSGI asset allowlist",
    )
    marker = '    script = _OVERLAY / "web/full-session.js"'
    text = require_one(
        text, marker,
        '    if hashlib.sha256((_OVERLAY / "web/cut-editor.js").read_bytes()).hexdigest() != "'
        + changes[CUT]
        + '":\n        raise RuntimeError("Stage cut-editor mismatch")\n'
        + marker,
        "WSGI cut-editor digest",
    )
    wsgi.write_text(text)

    manifest = dict(old_integrity)
    manifest[CUT] = changes[CUT]
    for name in manifest:
        file = dest / name
        if not file.is_file() or file.is_symlink():
            raise ValueError("Asset missing or symlink: " + name)
        manifest[name] = digest(file)
    (dest / "integrity.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    if any(digest(dest / name) != value for name, value in manifest.items()):
        raise ValueError("Merged asset integrity failed")
    if b"/montara/mix/projects" not in (dest / "web/montara.js").read_bytes():
        raise ValueError("Audio #379 regressed")
    if b"X-Montara-Stage-Origin" not in (
        dest / "urano/native_owner_web_gateway.py"
    ).read_bytes():
        raise ValueError("Stage tracing absent")
    for file in dest.rglob("*"):
        file.chmod(0o755 if file.is_dir() else 0o644)
    print("CANDIDATE_ONLY", dest, "files", len(manifest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for key in ("live", "base", "stage", "dest"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    build(args.live, args.base, args.stage, args.dest)
