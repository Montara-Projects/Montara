'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../urano/native_owner_browser_bridge.js'),'utf8');
const start=source.indexOf('  const reviewBlobs = new Map();');
const end=source.indexOf('  const decorateReview = async response =>');
assert(start>0 && end>start);
const reviewBlock=source.slice(start,end);
const location={origin:'https://montara.test',href:'https://montara.test/urano/v1/native/'};
let count=0,converted=0,mode='always-202';
const originalObjectURL=URL.createObjectURL;
const patchedURL=class extends URL {
  static createObjectURL(blob) {
    converted+=1;
    assert(blob.type.startsWith('video/mp4') || blob.type==='application/octet-stream');
    return 'blob:verified-video';
  }
};
const window={
  fetch: async () => {
    count++;
    if(mode==='always-202')
      return new Response(JSON.stringify({status:'preparing'}),{status:202,headers:{'Content-Type':'application/json'}});
    if(mode==='wrong-content')
      return new Response(JSON.stringify({status:'something else'}),{status:200,headers:{'Content-Type':'application/json'}});
    if(mode==='gateway-503')
      return new Response(JSON.stringify({error:'Private Engine unavailable'}),{status:503,headers:{'Content-Type':'application/json','X-Montara-Stage-Origin':'owner-gateway'}});
    if(mode==='ready-after-one' && count===1)
      return new Response('{}',{status:202,headers:{'Content-Type':'application/json'}});
    return new Response(new Uint8Array([0,0,0,0,102,116,121,112]),{status:200,headers:{'Content-Type':'video/mp4'}});
  }
};
const context={window,location,URL:patchedURL,setTimeout:fn=>setTimeout(fn,0)};
vm.runInNewContext(reviewBlock+'\nglobalThis.testReviewBlob=reviewBlob;',context);
(async () => {
  await assert.rejects(
    context.testReviewBlob('/api/v1/wizard/review/preview/0?v=stuck'),
    /still preparing/i);
  assert.equal(count,150);
  assert.equal(converted,0,'202 JSON must never become a video blob');

  count=0;mode='wrong-content';
  await assert.rejects(
    context.testReviewBlob('/api/v1/wizard/review/preview/0?v=json'),
    /not an MP4/i);
  assert.equal(converted,0,'JSON response must never become video');

  count=0;mode='gateway-503';
  await assert.rejects(
    context.testReviewBlob('/api/v1/wizard/review/preview/0?v=owner503'),
    /preview unavailable/i);
  assert.equal(count,1,'never automatically replay a gateway error');
  assert.equal(converted,0);

  count=0;mode='ready-after-one';
  const ready=await context.testReviewBlob('/api/v1/wizard/review/preview/0?v=ready');
  assert.equal(ready,'blob:verified-video');
  assert.equal(count,2);
  assert.equal(converted,1);

  count=0;
  await assert.rejects(
    context.testReviewBlob('/api/v1/wizard/review/preview/0?v=cancel',()=>false),
    /canceled/);
  assert.equal(count,0);
  console.log('STAGE_HOVER_202_TERMINAL_PASS');
})().catch(err=>{console.error(err);process.exitCode=1;});
