const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('web/montara.js', 'utf8');
const start = source.indexOf('const sessionImportTimes =');
const end = source.indexOf('function addFiles(', start);
assert.ok(start > 0 && end > start, 'benchmark hooks must live in the real import flow');

function setup() {
  let now = 0;
  const logs = [];
  const state = { platform:'youtube', files:[], uploads:0 };
  const context = {
    state,
    $: () => ({ checked:true }),
    isAudioEntry: f => f.kind === 'songs',
    performance:{now:()=>now},
    resetMontaraSuccessfulPutWindow:()=>{},
    montaraSuccessfulPutSummary:()=>({successful_put_acks:5, first_to_last_successful_put_sec:42.5}),
    console:{info:(...args)=>logs.push(args)}
  };
  const hooks = vm.runInNewContext(source.slice(start, end) + ';({sessionImportTimes, noteSessionImportIntent, noteSessionFilesAccepted, noteSessionAllPreviewsReady, noteSessionDetectionStart, noteSessionReviewInteractive})', context);
  return {state,logs,hooks,at:t=>{now=t}};
}

test('real Full session journey keeps picker/drop, preview and usable events separate',()=>{
  const t=setup();
  t.at(1000);t.hooks.noteSessionImportIntent();
  t.at(5000);t.hooks.noteSessionFilesAccepted([{},{}]);
  t.state.files=[{kind:'songs',preview:true,path:'private-A'},{kind:'songs',preview:true,path:'private-B'}];
  t.state.uploads=1;
  t.at(15000);t.hooks.noteSessionAllPreviewsReady();
  assert.equal(t.logs.length,0,'not ready while any upload is active');
  t.state.uploads=0;
  t.at(20000);t.hooks.noteSessionAllPreviewsReady();
  assert.equal(t.logs.length,1);
  assert.equal(t.logs[0][1].step,'all_previews_ready');
  assert.equal(t.logs[0][1].accepted_to_previews_sec,15);
  assert.equal(t.logs[0][1].intent_to_previews_sec,19);
  assert.equal(t.logs[0][1].successful_put_acks,5);
  assert.equal(t.logs[0][1].first_to_last_successful_put_sec,42.5);
  t.hooks.noteSessionAllPreviewsReady();
  assert.equal(t.logs.length,1,'no duplicate preview-ready event');
  t.at(25000);t.hooks.noteSessionDetectionStart();
  t.at(26000);t.hooks.noteSessionReviewInteractive({songs:[]});
  assert.equal(t.logs.length,1,'loading screen does not count as usable');
  t.at(31000);t.hooks.noteSessionReviewInteractive({songs:[{id:1}]});
  assert.equal(t.logs.length,2);
  assert.equal(t.logs[1][1].step,'songs_review_interactive');
  assert.equal(t.logs[1][1].accepted_to_usable_sec,26);
  assert.equal(t.logs[1][1].intent_to_usable_sec,30);
  assert.equal(t.logs[1][1].after_all_previews_sec,11);
  assert.equal(t.logs[1][1].detection_and_review_sec,6);
  assert.ok(!JSON.stringify(t.logs).includes('private-A'));
  assert.ok(!JSON.stringify(t.logs).includes('private-B'));
});
test('no false preview-ready event for incomplete or invalid audio sources',()=>{
  const t=setup();t.hooks.noteSessionFilesAccepted([{}]);
  t.state.files=[{kind:'songs',preview:false,path:'master'}];
  t.at(1200);t.hooks.noteSessionAllPreviewsReady();
  assert.equal(t.logs.length,0);
  t.state.files[0].preview=true;t.state.files[0].path='';
  t.hooks.noteSessionAllPreviewsReady();
  assert.equal(t.logs.length,0);
  t.state.files[0].path='private path';t.state.files.push({kind:'songs',preview:false,path:'missing'});
  t.hooks.noteSessionAllPreviewsReady();
  assert.equal(t.logs.length,0);
});
test('instrumentation is in the actual Full session and upload queue paths',()=>{
  const full=fs.readFileSync('web/full-session.js','utf8');
  const upload=fs.readFileSync('web/resumable-upload.js','utf8');
  assert.match(source,/noteSessionFilesAccepted\(list\)/);
  assert.match(source,/noteSessionAllPreviewsReady\(\);/);
  assert.match(full,/if \(!forVideo\) noteSessionDetectionStart\(\)/);
  assert.match(full,/drawSessionSongs\(data.songs\);\s*noteSessionReviewInteractive\(data\)/);
  assert.match(upload,/queue_wait_sec:/);
  assert.match(upload,/preflight_sec:/);
  assert.match(upload,/markMontaraSuccessfulPut\(\)/);
});

test('PUT ACK span is its own metric, not the preview-ready or first-usable wall time',()=>{
  const upload=fs.readFileSync('web/resumable-upload.js','utf8');
  const begin=upload.indexOf('const montaraSuccessfulPutWindow =');
  const end=upload.indexOf('async function sendResumableUpload(',begin);
  assert.ok(begin > 0 && end > begin);
  let now=0;
  const api=vm.runInNewContext(upload.slice(begin,end) +
    ';({resetMontaraSuccessfulPutWindow,markMontaraSuccessfulPut,montaraSuccessfulPutSummary})',
    {performance:{now:()=>now}});
  const result=()=>api.montaraSuccessfulPutSummary();
  assert.equal(result().successful_put_acks,0);
  assert.equal(result().first_to_last_successful_put_sec,null);
  now=1000;api.markMontaraSuccessfulPut();
  assert.equal(result().first_to_last_successful_put_sec,0);
  now=3200;api.markMontaraSuccessfulPut();
  now=5800;api.markMontaraSuccessfulPut();
  assert.equal(result().successful_put_acks,3);
  assert.equal(result().first_to_last_successful_put_sec,4.8);
  api.resetMontaraSuccessfulPutWindow();
  assert.equal(result().successful_put_acks,0);
  assert.equal(result().first_to_last_successful_put_sec,null);
});
