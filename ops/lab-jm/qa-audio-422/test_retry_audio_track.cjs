'use strict';
const {test}=require('node:test'), assert=require('node:assert/strict');
const {retryAudioTrack}=require('./retry_audio_track');
const jobId='a'.repeat(32),payloadJson='{"original":{"opaque":true}}';
function setup(statuses,signal) {
 let grants=0;const requests=[],states=[],delays=[];
 const args={jobId,payloadJson,signal,
  grant:async()=>`grant-${++grants}`,
  send:async req=>{requests.push(req);const next=statuses.shift();return {ok:next.ok||false,status:next.status||200,json:async()=>next.body||{}};},
  sleep:async(ms)=>{delays.push(ms)},onState:state=>states.push(state)};
 return {args,requests,states,delays,get grants(){return grants}};
}
test('transient per-track failure reuses identical ID/payload with fresh grants, max three attempts',async()=>{
 const h=setup([{status:503,body:{retryable:true,code:'AUDIO_TEMPORARY_IO'}},{status:503,body:{retryable:true,code:'AUDIO_TEMPORARY_TIMEOUT'}},{ok:true,status:200}]);
 assert.equal((await retryAudioTrack(h.args)).status,200);
 assert.equal(h.requests.length,3);assert.equal(h.grants,3);
 assert(h.requests.every(r=>r.jobId===jobId&&r.payloadJson===payloadJson));
 assert.deepEqual(h.requests.map(r=>r.grant),['grant-1','grant-2','grant-3']);
 assert.deepEqual(h.delays,[400,800]);
 assert.equal(h.states.at(-1).status,'ready');
});
test('generic 422 is permanent, no retry, no extra grant',async()=>{
 const h=setup([{status:422,body:{error:'old generic 422'}}]);
 await assert.rejects(retryAudioTrack(h.args),e=>e.status===422);assert.equal(h.grants,1);
});
test('authorization, payload and missing source failures never retry',async()=>{
 for(const status of [400,403,404,409,415,422]) {
  const h=setup([{status,body:{code:'AUDIO_INVALID_REQUEST',retryable:false}}]);
  await assert.rejects(retryAudioTrack(h.args));assert.equal(h.requests.length,1);
 }
});
test('only explicitly whitelisted failure code can auto retry',async()=>{
 const h=setup([{status:503,body:{code:'AUDIO_PREPARATION_FAILED',retryable:true}}]);
 await assert.rejects(retryAudioTrack(h.args));assert.equal(h.requests.length,1);
});
test('transient never exceeds three, preserves other tracks outside retry helper',async()=>{
 const h=setup(Array.from({length:4},()=>({status:503,body:{code:'AUDIO_TEMPORARY_IO',retryable:true}})));
 await assert.rejects(retryAudioTrack(h.args));assert.equal(h.requests.length,3);
 assert.equal(h.states.at(-1).status,'failed');
});
test('already cancelled signal prevents any attempt',async()=>{
 const ctl=new AbortController();ctl.abort();const h=setup([],ctl.signal);
 await assert.rejects(retryAudioTrack(h.args),e=>e.name==='AbortError');assert.equal(h.grants,0);
});
