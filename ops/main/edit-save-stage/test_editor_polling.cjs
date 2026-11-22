'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(process.argv[2],'utf8');
const start='function pollFrames() {\n';
const end='async function openFrames() {';
assert.equal(source.split(start).length,2);
const begin=source.indexOf(start);assert.ok(begin>=0);const finish=source.indexOf(end,begin);assert.ok(finish>begin);const block=source.slice(begin,finish);
const state={framesPoll:0,frameMutationBusy:false,waitingFrames:false,reviewShotCount:305,framesPending:true};
const frames={hidden:false};
let dialogOpen=false,refreshCalls=0,timerCB=null,timerDelay=null;
const document={querySelector:s=>s==='dialog.cut-dialog[open]' && dialogOpen?{}:null};
const ctx={
  state,document,
  $:id=>{assert.equal(id,'#frames');return frames;},
  clearTimeout:()=>{},
  setTimeout:(f,ms)=>{timerCB=f;timerDelay=ms;return 123;},
  refreshFrames:async()=>{refreshCalls+=1;},
  fail:e=>{throw e;},
};
vm.runInNewContext(block+';this.pollFrames=pollFrames;',ctx);
ctx.pollFrames();
assert.equal(timerDelay,12000);
assert.equal(refreshCalls,0);
dialogOpen=true;
timerCB();
setImmediate(async()=>{
  assert.equal(refreshCalls,0,'No polling should compete with Edit dialog');
  dialogOpen=false;
  ctx.pollFrames();
  await timerCB();
  assert.equal(refreshCalls,1,'Polling resumes with dialog closed');
  state.frameMutationBusy=true;
  const before=timerDelay;
  ctx.pollFrames();
  assert.equal(timerDelay,before,'Mutation in progress cannot schedule new poll');
  console.log('MAIN_305_EDIT_POLLING_PASS paused in dialog, 12s long-stage cadence, mutation busy blocks new poll');
});
