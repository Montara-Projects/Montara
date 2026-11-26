'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const src=fs.readFileSync(path.join(__dirname,'../web/montara.js'),'utf8');
test('session import limits preparation AND transfer to three slots',async()=>{
 const start=src.indexOf('const sessionImportLane=');
 const end=src.indexOf('async function uploadSmallNow(',start);
 assert(start>=0 && end>start);
 let active=0,peak=0,done=0;
 const state={audioTask:'session',uploads:0};
 const ctx=vm.createContext({state,montaraCompanion:{isAudio:()=>true},renderFiles(){},uploadSmallNow:async()=>{peak=Math.max(peak,++active);await new Promise(r=>setImmediate(r));await new Promise(r=>setImmediate(r));active--;done++;}});
 vm.runInContext(src.slice(start,end)+';globalThis.run=uploadSmall;',ctx);
 await Promise.all(Array.from({length:30},(_,i)=>ctx.run({name:i+'.wav'},{memory:{task:'session'}})));
 assert.equal(peak,3);assert.equal(done,30);assert.equal(state.uploads,0);
});
