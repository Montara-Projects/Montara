'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const crypto=require('node:crypto');
const path=require('node:path');
const base=path.resolve(__dirname,'..');
const read=p=>fs.readFileSync(path.join(base,p));
const sha=p=>crypto.createHash('sha256').update(read(p)).digest('hex');
const wrapper=read('deploy/candidates/jmlab_stage359_pr361_378_wsgi.py').toString();
const surface=read('urano/native_owner_browser_surface.py').toString();
for(const file of [
  'urano/native_owner_browser_bridge.js',
  'urano/native_owner_web_gateway.py',
  'urano/native_owner_browser_surface.py',
  'web/montara.js',
  'web/cut-editor.js'
]) assert(wrapper.includes(sha(file)), 'Missing preflight hash for '+file);
for(const file of ['web/montara.js','web/cut-editor.js','web/montara.css'])
  assert(surface.includes(sha(file)), 'Missing URL pin for '+file);
assert.equal(sha('web/full-session.js'),
  '004d2f6f14e53ef84e519a24c59ac2dd8384c2a86219fb92751cb62da482f824');
assert.equal(sha('web/montara.css'),
  '306c604a35feae0523236470f45a40dd1cd2a8b8c9cf56198eb286b233afa47e');
const editor=read('web/cut-editor.js').toString();
assert(editor.includes('Reload latest shot, keep my choices'));
assert(editor.includes("save.textContent='Saving…'"));
const montara=read('web/montara.js').toString();
assert(montara.includes('if (!partial) state.reviewShotCount = all.length;'));
assert(montara.includes('const partial = data.partial === true;'));
assert(montara.includes('frameThumbObserver.observe(img)'));
assert(montara.includes('state.frameMutationBusy=true'));
const gateway=read('urano/native_owner_web_gateway.py').toString();
assert(gateway.includes('X-Montara-Stage-Origin'));
assert(gateway.includes('Server-Timing'));
console.log('JM_STAGE_LIVE_OVERLAY_SHA_AND_REGRESSION_PASS');
