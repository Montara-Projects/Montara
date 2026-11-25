"""Real Chromium + real disposable Companion, no mocked permissions/health."""
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from urllib.request import urlopen

import pytest
from playwright.sync_api import sync_playwright
from e2e_journey import free_port

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def peers(tmp_path_factory):
    root = tmp_path_factory.mktemp('companion-permissions')
    (root / 'index.html').write_text('<!doctype html><html><head></head><body>Browser permission gate</body></html>')
    server = ThreadingHTTPServer(('127.0.0.1', 0),
             functools.partial(SimpleHTTPRequestHandler, directory=str(root)))
    origin = f'http://127.0.0.1:{server.server_port}'
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = free_port()
    base = f'http://127.0.0.1:{port}'
    env = {**os.environ, 'MONTARA_COMPANION_HOME': str(root / 'companion'),
           'MONTARA_COMPANION_PORT': str(port), 'MONTARA_COMPANION_ROOTS': str(root),
           'MONTARA_COMPANION_ORIGINS': re.escape(origin), 'PYTHONUNBUFFERED': '1'}
    with (root / 'companion.log').open('w') as log:
        process = subprocess.Popen([sys.executable, str(ROOT / 'companion/companion.py')],
                                   cwd=ROOT, env=env, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 15
            while True:
                assert process.poll() is None, 'Companion exited; inspect companion.log'
                try:
                    with urlopen(base + '/health', timeout=1) as response:
                        health = json.load(response)
                    break
                except OSError:
                    assert time.monotonic() < deadline, 'Disposable Companion did not start'
                    time.sleep(.1)
            assert health['app'] == 'montara-companion' and health['ffmpeg']
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                try:
                    yield browser, origin, base, health
                finally:
                    browser.close()
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            server.shutdown()
            server.server_close()


@pytest.mark.parametrize('repetition', range(3))
def test_real_permission_transition_controls_detection(peers, repetition):
    browser, origin, base, health = peers
    context = browser.new_context()
    try:
        page = context.new_page()
        requests = []
        page.on('request', lambda request: requests.append(request.url)
                if request.url.startswith(base) else None)
        page.goto(origin + '/index.html')
        page.add_script_tag(content=(ROOT / 'web/companion.js').read_text().replace(
            'http://127.0.0.1:47820', base))
        # Fresh Chromium 141 (Playwright 1.56): prompt is a real browser state.
        assert page.evaluate('montaraCompanion.permissionState()') == 'prompt'
        assert page.evaluate('montaraCompanion.detect()') is None
        assert requests == [], 'Prompt must not trigger a silent localhost probe'
        context.grant_permissions(['local-network-access'], origin=origin)
        assert page.evaluate('montaraCompanion.permissionState()') == 'granted'
        detected = page.evaluate('montaraCompanion.detect()')
        assert detected['app'] == health['app']
        assert detected['version'] == health['version']
        assert requests == [base + '/health']
        # Revoking browser permission must also clear a previously ready info.
        cdp = context.new_cdp_session(page)
        context_id = cdp.send('Target.getTargetInfo')['targetInfo']['browserContextId']
        cdp.send('Browser.setPermission', {'permission': {'name': 'local-network-access'},
                                          'setting': 'denied', 'origin': origin,
                                          'browserContextId': context_id})
        assert page.evaluate('montaraCompanion.permissionState()') == 'denied'
        assert page.evaluate('montaraCompanion.detect()') is None
        assert page.evaluate('montaraCompanion.info') is None
        assert requests == [base + '/health'], 'Denied must not probe localhost'
    finally:
        context.close()
