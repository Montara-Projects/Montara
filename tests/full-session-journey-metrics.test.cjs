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
  const hooks = vm.runInNewContext(source.slice(start, end) + ';({sessionImportTimes, noteSessionImportIntent, noteSessionFilesAccepted, noteSessionAllPreviewsReady, noteSessionDetectionStart, noteSessionReviewInteractive, recordSessionAudioPreparation, sessionAudioPreparationSummary, resetSessionAudioPreparationWindow})', context);
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
test('concurrent Companion preparations aggregate elapsed wall time, never sum stems',()=>{
  const t=setup();
  t.hooks.noteSessionFilesAccepted([{}]);
  t.hooks.recordSessionAudioPreparation(1000,9000,true);
  t.hooks.recordSessionAudioPreparation(2000,11000,true);
  t.hooks.recordSessionAudioPreparation(4000,5000,false);
  const summary=t.hooks.sessionAudioPreparationSummary();
  assert.equal(summary.companion_audio_preparations,3);
  assert.equal(summary.companion_audio_preparation_unavailable,1);
  assert.equal(summary.companion_audio_prep_wall_sec,10);
  t.state.files=[{kind:'songs',preview:true,path:'private'}];
  t.at(12000);t.hooks.noteSessionAllPreviewsReady();
  assert.equal(t.logs.length,1);
  assert.equal(t.logs[0][1].companion_audio_prep_wall_sec,10);
  assert.equal(t.logs[0][1].companion_audio_preparation_unavailable,1);
  t.hooks.resetSessionAudioPreparationWindow();
  assert.equal(t.hooks.sessionAudioPreparationSummary().companion_audio_prep_wall_sec,null);
  assert.equal(t.hooks.sessionAudioPreparationSummary().companion_audio_preparations,0);
});

test('sample placeholder does not suppress timing for first real Full session import',()=>{
  const t=setup();
  t.state.files=[{kind:'songs',sample:true,path:'demo'}];
  t.at(1000);t.hooks.noteSessionImportIntent();
  t.at(2000);t.hooks.noteSessionFilesAccepted([{}]);
  t.state.files=[{kind:'songs',preview:true,path:'real track'}];
  t.at(5000);t.hooks.noteSessionAllPreviewsReady();
  assert.equal(t.logs.length,1);
  assert.equal(t.logs[0][1].intent_to_previews_sec,4);
  assert.equal(t.logs[0][1].accepted_to_previews_sec,3);
  assert.ok(!JSON.stringify(t.logs).includes('real track'));
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


test('Companion audio preview preparation is timed independently of upload without filenames', async () => {
  const mainSource=fs.readFileSync('web/montara.js','utf8');
  const begin=mainSource.indexOf('async function uploadSmall(file, entry) {');
  const end=mainSource.indexOf('function upload(file, entry)',begin);
  assert.ok(begin>0 && end>begin);
  const script=mainSource.slice(begin,end)+';uploadSmall';
  const logs=[];
  const transferred=[];
  let now=1000;
  const original={
    name:'CONFIDENTIAL-live-jam.wav',
    size:120*1048576
  };
  const prepared={size:8*1048576};
  const state={uploads:0,platform:'youtube',audioTask:null};
  const context={
    state,
    $:()=>({checked:true}),
    sessionImportMode:()=>true,
    sessionSeconds:ms=>+(ms/1000).toFixed(2),
    montaraCompanion:{
      info:{version:'test'},
      isAudio:f=>f===original,
      isVideo:()=>false,
      smallVersion:async (_file,callback,_cancel,opts)=>{
        assert.equal(opts.preview,true);
        now=4300;
        return {file:prepared,preview:true,original:null};
      }
    },
    LONG_AUDIO_BYTES:20*1048576,
    performance:{now:()=>now},
    renderFiles:()=>{},
    remember:()=>{},
    upload:(file)=>transferred.push(file),
    console:{
      info:(label,data)=>logs.push({label,data}),
      warn:()=>{}
    }
  };
  const uploadSmall=vm.runInNewContext(script,context);
  const entry={removed:false,progress:0};
  await uploadSmall(original,entry);
  assert.equal(state.uploads,0);
  assert.equal(entry.preview,true);
  assert.equal(transferred.length,1);
  assert.equal(transferred[0],prepared);
  assert.equal(logs.length,1);
  assert.equal(logs[0].label,'[Montara full-session timing]');
  const event=logs[0].data;
  assert.equal(event.step,'companion_audio_preparation');
  assert.equal(event.status,'ready');
  assert.equal(event.preview_requested,true);
  assert.equal(event.preparation_sec,3.3);
  assert.equal(event.source_mib,120);
  assert.equal(event.prepared_mib,8);
  assert.ok(!JSON.stringify(logs).includes(original.name),
    'telemetry must never include a filename or source path');
});

test('failed Companion preparation is classified without falsifying transfer timing', async () => {
  const src=fs.readFileSync('web/montara.js','utf8');
  const begin=src.indexOf('async function uploadSmall(file, entry) {');
  const end=src.indexOf('function upload(file, entry)',begin);
  const script=src.slice(begin,end)+';uploadSmall';
  const infos=[];
  let now=2000;
  const original={name:'TOP-SECRET-RECITAL.wav',size:4*1048576};
  const ctx={
    state:{uploads:0,platform:'youtube',audioTask:null},
    $:()=>({checked:true}),
    sessionImportMode:()=>true,
    sessionSeconds:ms=>+(ms/1000).toFixed(2),
    montaraCompanion:{
      info:{version:'test'},
      isAudio:()=>true,
      isVideo:()=>false,
      smallVersion:async()=>{now=3500;throw Error('Confidential local path')}
    },
    LONG_AUDIO_BYTES:20*1048576,
    performance:{now:()=>now},
    renderFiles:()=>{},
    remember:()=>{},
    upload:()=>{},
    console:{info:(label,data)=>infos.push(data),warn:()=>{}}
  };
  await vm.runInNewContext(script,ctx)(original,{removed:false});
  assert.equal(infos.length,1);
  assert.equal(infos[0].status,'unavailable');
  assert.equal(infos[0].prepared_mib,null);
  assert.equal(infos[0].preparation_sec,1.5);
  assert.ok(!JSON.stringify(infos).includes('TOP-SECRET'));
  assert.ok(!JSON.stringify(infos).includes('Confidential local path'));
});
