#!/usr/local/opt/python@3.11/bin/python3.11
"""Offline signed-hash, owner-consented LAB JM renderer-only .pkg installer.
Only modifies ~/.montara-companion/video program files; never project data,
local mixer, active render, launch agent, CORS preferences or other labs.
The user's macOS Installer consent is required before this code executes.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import pwd
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request

TARGET = "92c7bc33f59baae92a8d61e5dd4bf0ce9685d79e"
OLD = "3e92908b137a0f7b0959403a78802e5427981ca2"
FILES = ("engine", "venv", "brand", "local_video.py", "video_recipe.py", "ENGINE_COMMIT")
LABEL = "website.montara.companion"


def run(args, *, timeout=30, **kw):
    return subprocess.run(args, check=True, timeout=timeout, **kw)


def owner_cmd(name, uid, *command):
    return ["launchctl", "asuser", str(uid), "sudo", "-H", "-u", name, *command]


def listener():
    proc = subprocess.run(
        ["lsof", "-nP", "-t", "-iTCP:47820", "-sTCP:LISTEN"],
        capture_output=True, text=True, timeout=5,
    )
    value = proc.stdout.strip().splitlines()
    return value[0] if len(value) == 1 and value[0].isdigit() else None


def health():
    with urllib.request.urlopen("http://127.0.0.1:47820/health", timeout=3) as rsp:
        return json.load(rsp)


def validate_idle(owner, app):
    pid = listener()
    if not pid:
        raise RuntimeError("Existing Companion is not responding on its expected port")
    who = subprocess.check_output(["ps", "-p", pid, "-o", "user="], text=True).strip()
    command = subprocess.check_output(["ps", "-p", pid, "-o", "command="], text=True).strip()
    if who != owner or str(app / "companion.py") not in command:
        raise RuntimeError("Companion port belongs to another process")
    info = health()
    if (info.get("app") != "montara-companion" or
        info.get("busy") is not False or
        (info.get("local_video") or {}).get("engine") != OLD):
        raise RuntimeError("Companion is active, unrecognized, or its Engine has changed")
    if subprocess.run(["pgrep", "-P", pid],capture_output=True,timeout=3).returncode == 0:
        raise RuntimeError("Companion still has a child process")
    return pid


def main():
    if os.geteuid() != 0 or platform.system() != "Darwin" or platform.machine() != "x86_64":
        raise RuntimeError("This private package requires macOS Installer on an Intel Mac")
    archive = Path(sys.argv[1])
    digestfile = Path(sys.argv[2])
    expected = digestfile.read_text().strip()
    if len(expected) != 64 or any(x not in "0123456789abcdef" for x in expected):
        raise RuntimeError("Invalid integrity manifest")
    digest = hashlib.sha256()
    with archive.open("rb") as file:
        while block := file.read(1024*1024):
            digest.update(block)
    if digest.hexdigest() != expected:
        raise RuntimeError("Package payload integrity check failed")
    console = subprocess.check_output(["stat","-f","%Su","/dev/console"],text=True).strip()
    if console in ("","root","loginwindow"):
        raise RuntimeError("Log into your Mac user account first")
    account = pwd.getpwnam(console)
    app = Path(account.pw_dir) / ".montara-companion"
    video = app / "video"
    plist = Path(account.pw_dir) / "Library/LaunchAgents" / (LABEL + ".plist")
    if any(not p.exists() or p.is_symlink() for p in (app,video,plist,app/"companion.py")):
        raise RuntimeError("Expected user-owned Companion is not installed")
    if video.stat().st_uid != account.pw_uid:
        raise RuntimeError("Companion renderer belongs to a different user")
    config=plistlib.loads(plist.read_bytes())
    if (config.get("Label") != LABEL or
        config.get("ProgramArguments") != [str(app/"bin/montara-companion")]):
        raise RuntimeError("Unexpected managed Companion startup configuration")
    current = (video / "ENGINE_COMMIT").read_text().strip()
    if current == TARGET:
        print("The matching LAB JM renderer is already installed.")
        return
    if current != OLD:
        raise RuntimeError("Another Companion Engine is installed; do not replace it")
    if shutil.disk_usage(video).free < 1024*1024*1024:
        raise RuntimeError("Not enough free disk space to preserve the previous renderer")
    validate_idle(console, app)
    stage = Path(tempfile.mkdtemp(dir=video, prefix=".jm-install."))
    backup = None
    stopped = False
    swapped = False
    try:
        with tarfile.open(archive,"r:gz") as tf:
            members=tf.getmembers()
            if not members or any(
                Path(m.name).is_absolute() or ".." in Path(m.name).parts or
                Path(m.name).parts[0] not in FILES or
                m.islnk() or (m.issym() and not m.name.startswith("venv/bin/"))
                for m in members
            ):
                raise RuntimeError("Unsafe package archive content")
            tf.extractall(stage)
        if (stage/"ENGINE_COMMIT").read_text().strip()!=TARGET:
            raise RuntimeError("Mismatched renderer version inside package")
        if any(not (stage/f).exists() for f in FILES):
            raise RuntimeError("Missing renderer files in package")
        run(["chown","-R",console,str(stage)],timeout=35)
        smoke = ("import os,sys;os.chdir(sys.argv[1]);"
                 "import cv2,numpy,scipy;"
                 "from core.stages.export import ExportStage;"
                 "print('PINNED_ENGINE_IMPORT_OK')")
        run(["sudo","-H","-u",console,"env","ZUCKER_DATA_ROOT="+str(stage/"smoke"),
             str(stage/"venv/bin/python"),"-c",smoke,str(stage/"engine")],timeout=35)
        validate_idle(console,app)
        run(owner_cmd(console,account.pw_uid,"launchctl","bootout",
                      "gui/"+str(account.pw_uid)+"/"+LABEL))
        stopped=True
        if listener():
            raise RuntimeError("Companion listener remained active; aborting")
        backup=Path(tempfile.mkdtemp(dir=video,prefix=".before-jm-92."))
        swapped=True
        for file in FILES:
            existing=video/file
            if existing.exists() or existing.is_symlink():
                os.rename(existing,backup/file)
            os.rename(stage/file,existing)
        run(["chown","-R",console,*[str(video/f) for f in FILES]],timeout=40)
        run(owner_cmd(console,account.pw_uid,"launchctl","bootstrap",
                      "gui/"+str(account.pw_uid),str(plist)))
        for _ in range(35):
            time.sleep(1)
            try:
                v=health()
                if (v.get("app")=="montara-companion" and
                    (v.get("local_video") or {}).get("engine")==TARGET and
                    v.get("busy") is False):
                    print("LAB JM renderer active and verified:",TARGET[:8])
                    print("Previous renderer safely preserved in:",backup.name)
                    return
            except (OSError,TimeoutError,ValueError):
                continue
        raise RuntimeError("New renderer was not verified by the running Companion")
    except BaseException:
        if stopped:
            subprocess.run(owner_cmd(console,account.pw_uid,"launchctl","bootout",
                "gui/"+str(account.pw_uid)+"/"+LABEL),capture_output=True,timeout=10)
        if swapped and backup:
            for f in FILES:
                item=video/f
                if item.exists() or item.is_symlink():
                    os.rename(item,stage/("failed-"+f))
                old=backup/f
                if old.exists() or old.is_symlink():
                    os.rename(old,item)
        if stopped:
            subprocess.run(owner_cmd(console,account.pw_uid,"launchctl","bootstrap",
                "gui/"+str(account.pw_uid),str(plist)),capture_output=True,timeout=15)
        print("Renderer update aborted; original renderer restored where possible.")
        raise


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Montara LAB JM install failed:",type(exc).__name__,str(exc),file=sys.stderr)
        sys.exit(1)
