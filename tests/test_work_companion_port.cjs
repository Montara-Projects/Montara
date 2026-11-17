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
