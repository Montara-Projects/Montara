'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const companion = fs.readFileSync(path.join(__dirname, '..', 'web', 'companion.js'), 'utf8');

function videoUrl(hostname) {
  return vm.runInNewContext(
    companion + '\nmontaraCompanion.videoUrl("0123456789abcdef0123456789abcdef",true)',
    { location: { hostname } }
  );
}

test('Montara Work QA connects to its isolated Companion', () => {
  assert.equal(
    videoUrl('multisong.35-242-225-127.sslip.io'),
    'http://127.0.0.1:47828/video-renders/0123456789abcdef0123456789abcdef/file?download=1'
  );
});

test('Other Montara installations continue using the habitual Companion', () => {
  assert.equal(
    videoUrl('montara-tau.vercel.app'),
    'http://127.0.0.1:47820/video-renders/0123456789abcdef0123456789abcdef/file?download=1'
  );
});

test('Work QA version check uses the exact deployed Engine pin', () => {
  const montara = fs.readFileSync(path.join(__dirname, '..', 'web', 'montara.js'), 'utf8');
  assert.ok(montara.includes("location.hostname === 'multisong.35-242-225-127.sslip.io'"));
  assert.ok(montara.includes("expectedCompanionEngine='34c338d6d12e5d91e76b95e3e147714ea896cdf9'"));
  assert.ok(montara.includes("else if (!expectedCompanionEngine || force)"));
});

test('reports a blocked loopback permission without changing settings', async () => {
  const result = vm.runInNewContext(companion + '\nmontaraCompanion.loopbackPermission()', {
    location: {hostname:'multisong.35-242-225-127.sslip.io'},
    navigator: {permissions:{query:async ({name}) => {
      assert.equal(name, 'loopback-network');
      return {state:'denied'};
    }}}
  });
  assert.equal(await result, 'denied');
});

test('falls back to the older permission name without assuming a denial', async () => {
  const result = vm.runInNewContext(companion + '\nmontaraCompanion.loopbackPermission()', {
    location: {hostname:'multisong.35-242-225-127.sslip.io'},
    navigator: {permissions:{query:async ({name}) => {
      if (name === 'loopback-network') throw new TypeError();
      return {state:'prompt'};
    }}}
  });
  assert.equal(await result, 'prompt');
});
