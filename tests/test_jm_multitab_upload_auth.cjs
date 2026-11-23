'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const test=require('node:test');
const source=fs.readFileSync('urano/native_owner_browser_bridge.js','utf8');
const file=JSON.stringify({name:'Music and I.wav',size:12400,fingerprint:'a'.repeat(64)});

function networkPair(channels=true){
  let current='',rotations=0,uploads=0,denied=0;
  const boxes=[];
  const sameOrigin='https://montara-lab-jm.memoriainvalida001.workers.dev';
  class FakeBroadcast {
    constructor(name){this.name=name;this.onmessage=null;boxes.push(this);}
    postMessage(data){
      for(const box of boxes)if(box!==this&&box.name===this.name)
        box.onmessage?.({data});
    }
  }
  function open(){
    const requests=[];
    async function network(url,opts={}){
      requests.push({url,opts});
      if(url==='/urano/v1/session/refresh'){
        current=(++rotations).toString(16).padStart(64,'0');
        return new Response(JSON.stringify({csrf:current}),{
          status:200,headers:{'Content-Type':'application/json'}});
      }
      if(url==='/urano/v1/native/ensure'){
        return new Response(JSON.stringify({state:'ready',generation:12}),{
          status:200,headers:{'Content-Type':'application/json'}});
      }
      if(url==='/urano/v1/native/rpc/montara/uploads'){
        uploads++;
        const token=opts.headers?.get?.('X-Urano-CSRF');
        if(token!==current){
          denied++;
          return new Response(JSON.stringify({error:'Invalid private session'}),{
            status:403,headers:{'Content-Type':'application/json'}});
        }
        const body=JSON.parse(opts.body);
        if(body.name==='blocked.wav')
          return new Response(JSON.stringify({error:'Origin denied'}),{
            status:403,headers:{'Content-Type':'application/json'}});
        return new Response(JSON.stringify({id:'b'.repeat(32),received:0,chunk_size:4096,complete:false}),{
          status:200,headers:{'Content-Type':'application/json'}});
      }
      if(url==='/urano/v1/native/rpc/montara/uploads/'+('b'.repeat(32)) &&
         opts.method==='PUT'){
        uploads++;
        if(opts.headers.get('X-Urano-CSRF')!==current){
          denied++;
          return new Response(JSON.stringify({error:'Invalid private session'}),{
            status:403,headers:{'Content-Type':'application/json'}});
        }
        return new Response(JSON.stringify({received:opts.body.size}),{
          status:200,headers:{'Content-Type':'application/json'}});
      }
      throw Error('unexpected request '+url);
    }
    const window={fetch:network};
    const native={
      window,document:{addEventListener:()=>{},getElementById:()=>null},
      location:{href:sameOrigin+'/urano/v1/native/',origin:sameOrigin},
      BroadcastChannel:channels?FakeBroadcast:undefined,
      URL,Response,Headers,URLSearchParams,Blob,ArrayBuffer,XMLHttpRequest:undefined,
      HTMLMediaElement:undefined,HTMLVideoElement:undefined,
      HTMLAudioElement:undefined,HTMLImageElement:undefined,
      setTimeout,clearTimeout
    };
    vm.runInNewContext(source,native);
    return {fetch:window.fetch,requests};
  }
  return {
    open,
    post(tab,name='Music and I.wav'){
      return tab.fetch('/montara/uploads',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({...JSON.parse(file),name})
      });
    },
    chunk(tab){
      return tab.fetch('/montara/uploads/'+('b'.repeat(32)),{
        method:'PUT',headers:{'Upload-Offset':'0','Content-Type':'application/octet-stream'},
        body:new Blob([new Uint8Array([1,2,3,4])])
      });
    },
    counts(){return {rotations,uploads,denied};}
  };
}

test('two tabs authenticate independently and recover stale csrf on upload',async()=>{
  const app=networkPair(false);
  const video=app.open(),audio=app.open();
  assert.equal((await app.post(video)).status,200);
  assert.equal((await app.post(audio)).status,200);
  assert.equal((await app.post(video)).status,200);
  assert.deepEqual(app.counts(),{rotations:3,uploads:4,denied:1});
});

test('old-tab upload retries exactly once on specific CSRF 403 without broadcast',async()=>{
  const app=networkPair(false);
  const video=app.open(),audio=app.open();
  assert.equal((await app.post(video)).status,200);
  assert.equal((await app.post(audio)).status,200);
  assert.equal((await app.post(video)).status,200);
  assert.deepEqual(app.counts(),{rotations:3,uploads:4,denied:1});
  assert.equal(video.requests.filter(v=>v.url==='/urano/v1/session/refresh').length,2);
  const forbidden=await app.post(video,'blocked.wav');
  assert.equal(forbidden.status,403);
  assert.deepEqual(app.counts(),{rotations:3,uploads:5,denied:1});
});


test('an audio Blob chunk can resume across the two tabs after CSRF rotates',async()=>{
  const app=networkPair(false);
  const audio=app.open(),video=app.open();
  assert.equal((await app.post(audio)).status,200);
  assert.equal((await app.post(video)).status,200);
  const chunk=await app.chunk(audio);
  assert.equal(chunk.status,200);
  assert.equal((await chunk.json()).received,4);
  assert.deepEqual(app.counts(),{rotations:3,uploads:4,denied:1});
});
