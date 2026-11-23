const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');
const cut = fs.readFileSync('web/cut-editor.js','utf8');
const main = fs.readFileSync('web/montara.js','utf8');
const bridge = fs.readFileSync('urano/native_owner_browser_bridge.js','utf8');

test('new Stage edit sources parse safely', ()=>{
  new vm.Script(cut);
  new vm.Script(main);
  new vm.Script(bridge);
});
test('Edit reuses the existing encoded thumbnail motion preview', ()=>{
  assert.match(cut, /reviewThumb\?\.dataset\.preview/);
  assert.match(cut, /reviewVideo\.src=previewUrl/);
  assert.match(cut, /reviewVideo\.controls=true/);
  assert.match(cut, /playButton\.textContent='Play review'/);
  assert.match(cut, /reviewVideo\.addEventListener\('timeupdate',updatePlaybackMarker\)/);
  assert.match(cut, /indicator\.className='music-cut-playhead'/);
  assert.match(cut, /activeFraming\(\)\.after\(review,zoomArea\)/);
  assert.match(cut, /activeFraming\(\)\.hidden=true/);
  assert.match(cut, /frameButton\.textContent='Edit framing'/);
  assert.doesNotMatch(cut, /openMusicShot\(index,recoveredDraft/);
});
test('boundary edits can refresh a changed video preview', ()=>{
  assert.match(cut, /onSaved:saved=>/);
  assert.match(cut, /reviewVideo\.pause\(\)/);
  assert.match(cut, /refreshMusicReview\(index\)\.then/);
  assert.match(cut, /reviewVideo\.src=thumb\.dataset\.preview/);
});
test('one Save Shot with guarded silent revision repair; no reload button', ()=>{
  assert.match(cut, /const sameOriginal=/);
  assert.match(cut, /if\(!sameOriginal\(base,latest\)\)/);
  assert.match(cut, /await persist\(latest\)/);
  assert.match(cut, /defaultButton\.textContent='Default'/);
  assert.match(cut, /dialog\.close\(\);\s*\$\('#musicCutStatus'\)/);
  assert.doesNotMatch(cut, /Reload latest shot, keep my choices/);
  assert.doesNotMatch(cut, /cut-conflict-actions/);
});
test('new Audio projects persist before media buffers finish loading', ()=>{
  const plan=main.indexOf('mix.plan = { ...ready.plan');
  const save=main.indexOf('if(audioOnly()&&!restoredProject)',plan);
  const buffers=main.indexOf('await loadBuffers()',plan);
  assert.ok(plan>=0&&save>plan&&buffers>save);
  assert.match(main,/await saveAudioProject\(\);/);
  assert.match(main,/project_id:mix\.project\?\.id \|\| null/);
});
test('video shelf disambiguates duplicate saved names without changing paths',()=>{
  assert.match(bridge, /const duplicate=rows\.filter/);
  assert.match(bridge, /const uniqueLabel=duplicate/);
  assert.match(bridge, /open\.textContent = uniqueLabel/);
  assert.match(bridge, /body:JSON\.stringify\(\{path:project\.path\}\)/);
});
