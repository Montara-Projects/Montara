'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const src=fs.readFileSync(__dirname+'/../web/full-session.js','utf8');
const b=src.indexOf('async function syncSessionMastersToProject('),e=src.indexOf('const savedSongName=',b);
assert(b>0&&e>b);
const fn=src.slice(b,e);
test('finished songs are copied into the project folder selected at Continue',async()=>{
 const saved=[],calls=[];
 const data={songs:[{id:1,name:'First',start:0},{id:2,name:'Second',start:60}],results:[{id:1,name:'First',start:0},{id:2,name:'Second',start:60}]};
 const ctx={
  sessionDownloads:{projectSaving:false,saved:new Set()},
  state:{localProject:{id:'b'.repeat(16),folder:'/users/Montara/Project'}},
  fullSession:{id:'a'.repeat(12)},
  getSessionMasterBlob:async s=>{calls.push(s.id);return new Blob(['ID3']);},
  montaraCompanion:{saveInProject:async(id,name,blob)=>{saved.push([id,name,blob.size]);}},
  savedSongName:(s,i)=>(i+1)+' - '+s.name+'.mp3',toast:m=>calls.push(m),console,Blob
 };
 vm.createContext(ctx);vm.runInContext(fn+';globalThis.sync=syncSessionMastersToProject;',ctx);
 await ctx.sync(data);
 assert.equal(saved.length,2);assert(saved[0][1].includes('First'));
 await ctx.sync(data);
 assert.equal(saved.length,2,'already saved songs not uploaded twice');
});
test('Full Session Continue explicitly selects a local project before new session starts',()=>{
 const begin=src.indexOf('async function openFullSession('),end=src.indexOf('async function mixSessionForVideo(',begin);
 const text=src.slice(begin,end);
 assert(text.indexOf('montaraCompanion.projectFolder(')<text.indexOf("api('/montara/session'"));
 assert(text.includes('montara-project-folder-'));
});
