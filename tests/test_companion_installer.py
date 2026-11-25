"""Run the real installer guard with isolated commands; never bind the real port."""
import os
import re
import shlex
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import pytest

INSTALLER=Path(__file__).resolve().parents[1]/'companion/install.sh'


def test_declared_installer_payload_passes_real_offline_selftest(tmp_path):
    """Import the actual declared payload, not modules from the source tree."""
    files = ['companion.py']
    for declarations in re.findall(r'^for f in (.+); do$', INSTALLER.read_text(), re.M):
        files.extend(shlex.split(declarations))
    payload = tmp_path / 'payload'
    for name in files:
        target = payload / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(INSTALLER.parent / name, target)
    env = {**os.environ, 'PYTHONPATH': '',
           'MONTARA_COMPANION_HOME': str(tmp_path / 'home'),
           'MONTARA_COMPANION_BUNDLE_SELFTEST': '1'}
    result = subprocess.run([sys.executable, str(payload / 'companion.py')],
                            cwd=tmp_path, env=env, text=True,
                            capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert 'MONTARA_COMPANION_BUNDLE_SELFTEST_PASS' in result.stdout


def command(folder,name,body):
    path=folder/name;path.write_text('#!/bin/sh\n'+body+'\n');path.chmod(0o755)


@pytest.mark.parametrize('own',[False,True])
def test_update_stops_only_its_idle_companion_before_replacing_program(tmp_path,own):
    home=tmp_path/'home';home.mkdir();app=home/'.montara-companion';app.mkdir()
    script=app/'companion.py';script.write_text('import time\ntime.sleep(180)\n')
    # Our child has no port. lsof is isolated to report only this test PID.
    process=subprocess.Popen([sys.executable,str(script)])
    waiter=threading.Thread(target=process.wait,daemon=True);waiter.start()
    bin_=tmp_path/'bin';bin_.mkdir();(bin_/'python3').symlink_to(sys.executable)
    command(bin_,'ffmpeg','exit 0')
    command(bin_,'lsof',f'echo {process.pid}')
    command(bin_,'pgrep','exit 1')
    if not own:command(bin_,'ps','echo /another/application.py')
    command(bin_,'curl',f'''case "$*" in
  */health*) echo '{{"app":"montara-companion","busy":false}}'; exit 0;;
esac
touch "{tmp_path}/download-started"; exit 22''')
    env={**os.environ,'HOME':str(home),'PATH':str(bin_)+os.pathsep+os.environ['PATH'],'MONTARA_NO_SHELL_SETUP':'1'}
    try:
        result=subprocess.run(['bash',str(INSTALLER)],env=env,text=True,capture_output=True,timeout=60)
        assert result.returncode!=0 # Deliberate simulated download failure after the guard.
        if own:
            waiter.join(timeout=2);assert process.poll() is not None
            assert (tmp_path/'download-started').exists()
        else:
            assert process.poll() is None
            assert 'another application' in result.stdout
            assert not (tmp_path/'download-started').exists()
        assert script.read_text()=='import time\ntime.sleep(180)\n'
        assert not (home/'.zshrc').exists()
    finally:
        if process.poll() is None:process.terminate()
        waiter.join(timeout=3)
