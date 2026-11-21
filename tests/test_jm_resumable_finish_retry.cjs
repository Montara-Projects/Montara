'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(__dirname+'/../web/resumable-upload.js','utf8');
const start=source.indexOf('const FINISH_LANE_LIMIT = 2;');
const end=source.indexOf('const partLanes = ',start);
assert(start>0 && end>start && source.includes('finishOriginalUpload(job.id, progress, signal, cancelled)'));
function runner(api){
  let waits=0, statuses=[];
  const ctx={api,setTimeout:(cb)=>{waits++;setImmediate(cb);},
    Date,Error,console};
  vm.createContext(ctx);
  vm.runInContext(source.slice(start,end)+
    'globalThis.finish=finishOriginalUpload;globalThis.lane=finishLane;',ctx);
  return {ctx,waits:()=>waits,statuses};
}
test('finish recovers from 503 without resending bytes and reuses ID',async()=>{
  const paths=[];let attempt=0;
  const r=runner(async(path)=>{paths.push(path);if(++attempt<3)throw new Error('Request failed (503)');return {songs:[{path:'done'}]};});
  const progress=[];
  const result=await r.ctx.finish('a'.repeat(32),(...x)=>progress.push(x),null,()=>false);
  assert.equal(result.songs[0].path,'done');
  assert.equal(paths.length,3);
  assert(paths.every(p=>p==='/montara/uploads/'+ 'a'.repeat(32) + '/finish'));
  assert(progress.length===2);
  assert.equal(r.ctx.lane.active,0);
});
test('real 4xx fails immediately, never retries',async()=>{
  let calls=0;
  const r=runner(async()=>{calls++;throw new Error('Request failed (409)');});
  await assert.rejects(r.ctx.finish('b'.repeat(32),()=>{},null,()=>false),/409/);
  assert.equal(calls,1);assert.equal(r.ctx.lane.active,0);
});
test('abort after transient response stops further attempts',async()=>{
  let calls=0,aborted=false;
  const r=runner(async()=>{calls++;aborted=true;throw new Error('Request failed (503)');});
  await assert.rejects(r.ctx.finish('c'.repeat(32),()=>{},null,()=>aborted),/Upload removed/);
  assert.equal(calls,1);assert.equal(r.ctx.lane.active,0);
});
