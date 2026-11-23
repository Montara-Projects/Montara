'use strict';
const assert=require('node:assert/strict');
const test=require('node:test');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('urano/native_owner_browser_bridge.js','utf8');

test('authenticated browser displays queue position and resumes private upload',async()=>{
  const labels=[];
  const live=new Set();
  const document={
    addEventListener(){},
    getElementById(){return null;},
    createElement(name){
      const node={tag:name,setAttribute(){},style:{},remove(){live.delete(this);}};
      Object.defineProperty(node,'textContent',{set(v){labels.push(v);}});
      return node;
    },
    body:{append(node){live.add(node);}}
  };
  let attempts=0,refresh=0,uploads=0;
  const fetch=async(url,options)=>{
    if(url==='/urano/v1/session/refresh'){
      refresh++;
      return new Response(JSON.stringify({csrf:'a'.repeat(64)}),{
        status:200,headers:{'Content-Type':'application/json'}});
    }
    if(url==='/urano/v1/native/ensure'){
      attempts++;
      const reply=attempts<=2?
        {state:'queued',position:3-attempts}:
        {state:'ready',generation:8};
      return new Response(JSON.stringify(reply),{
        status:attempts<=2?202:200,
        headers:{'Content-Type':'application/json'}});
    }
    if(url==='/urano/v1/native/rpc/montara/uploads'){
      uploads++;
      return new Response(JSON.stringify({id:'b'.repeat(32),received:0}),{
        status:200,headers:{'Content-Type':'application/json'}});
    }
    throw new Error('Unexpected '+url);
  };
  const window={fetch};
  const sandbox={
    window,document,
    location:{origin:'https://montara-lab-jm.memoriainvalida001.workers.dev',
      href:'https://montara-lab-jm.memoriainvalida001.workers.dev/urano/v1/native/'},
    URL,URLSearchParams,Response,Headers,Blob,ArrayBuffer,
    XMLHttpRequest:undefined,HTMLMediaElement:undefined,
    HTMLImageElement:undefined,HTMLVideoElement:undefined,
    HTMLAudioElement:undefined,
    setTimeout:fn=>{queueMicrotask(fn);return 1;},clearTimeout(){}
  };
  vm.runInNewContext(source,sandbox);
  const res=await window.fetch('/montara/uploads',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name:'Music and I.wav',size:4})
  });
  assert.equal(res.status,200);
  assert.equal(attempts,3);
  assert.equal(uploads,1);
  assert.equal(live.size,0);
  assert.ok(labels.some(l=>l.includes('position 2')));
  assert.ok(labels.some(l=>l.includes('position 1')));
  assert.ok(labels.every(l=>!l.includes('minutes remaining')));
  assert.equal(refresh,1);
});
