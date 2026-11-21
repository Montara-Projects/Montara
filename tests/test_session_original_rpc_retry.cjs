const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {test}=require('node:test');
const src=fs.readFileSync(__dirname+'/../web/full-session.js','utf8');
const start=src.indexOf('async function fetchOriginalWindows(');
const end=src.indexOf('async function queueSongOriginals(',start);
assert(start>0&&end>start);
const body=src.slice(start,end);
test('a lost Owner GET /originals connection recovers before aborting 24-song export',async()=>{
 let requests=0;
 const status={textContent:''};
 const ctx={
  URLSearchParams,fullSession:{id:'abcdefabcdef'},checkSessionCancel:()=>{},
  $:()=>status,setTimeout:(fn)=>fn(),
  api:async path=>{
   requests++;
   assert(path.startsWith('/montara/session/abcdefabcdef/originals?song=3'));
   if(requests<3)throw Error('Lost the connection to Montara');
   return {originals:[{file:'voice.wav',window:[10,30],received:true}]};
  }
 };
 vm.createContext(ctx);
 vm.runInContext(body+';this.fetchOriginalWindows=fetchOriginalWindows;',ctx);
 const windows=await ctx.fetchOriginalWindows({id:3,start:10,end:30,name:'Music'});
 assert.equal(requests,3);
 assert.equal(windows.length,1);
});
