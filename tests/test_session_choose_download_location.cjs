'use strict';
const {test}=require('node:test'), assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(__dirname+'/../web/full-session.js','utf8');
const begin=source.indexOf('const sessionDownloads=');
const end=source.indexOf('const sessionResultCache =',begin);
assert(begin>0&&end>begin);
function context(){
 const calls=[],written=[];
 const entries=new Map();
 const ctx={
  window:{async showDirectoryPicker(){calls.push('choose-download-folder');return {
    async getFileHandle(name){const h={async createWritable(){return {async write(blob){written.push([name,blob.size]);},async close(){},async abort(){}};}};entries.set(name,h);return h;},
  };},async showSaveFilePicker(opts){calls.push('choose-file:'+opts.suggestedName);return {
    async createWritable(){return {async write(blob){written.push(['single',blob.size]);},async close(){},async abort(){}};}
  };}},
  fullSession:{id:'a'.repeat(12),data:{songs:[{id:1,name:'Song 01',start:0},{id:2,name:'Song 02',start:200}]}},
  montaraCompanion:{detect:async()=>null,info:null},
  fetch:async(path)=>{calls.push('fetch:'+path);return {
    ok:true,status:200,headers:{get:key=>key==='Content-Type'?'audio/mpeg':'3'},
    blob:async()=>new Blob(['ID3'],{type:'audio/mpeg'})
  };},
  Blob,Set,Date,Error,
  $:()=>({set textContent(value){calls.push('status:'+value);}}),
  toast:message=>calls.push('toast:'+message),
  console
 };
 vm.createContext(ctx);
 vm.runInContext(source.slice(begin,end)+';globalThis.download=downloadSessionMasters;',ctx);
 return {ctx,calls,written};
}
test('download all chooses directory FIRST, streams each MP3, no ZIP and no direct navigation',async()=>{
 const {ctx,calls,written}=context();
 await ctx.download([{id:1,name:'Song 01',start:0},{id:2,name:'Song 02',start:200}]);
 assert.equal(calls[0],'choose-download-folder');
 assert.equal(written.length,2);
 assert(written[0][0].startsWith('01 - Song 01'));
 assert(written[1][0].startsWith('02 - Song 02'));
 assert.equal(calls.filter(x=>x.startsWith('fetch:')).length,2);
 assert(calls.every(x=>!x.includes('.zip')));
});
test('single MP3 opens save-as before request',async()=>{
 const {ctx,calls,written}=context();
 await ctx.download([{id:1,name:'Song 01'}],{id:1,name:'Song 01'});
 assert(calls[0].startsWith('choose-file:'));
 assert.equal(written.length,1);
 assert(calls.some(x=>x.includes('?download=1')));
});
test('failed MP3 fails visibly and does not claim all songs downloaded',async()=>{
 const {ctx,calls}=context();
 ctx.fetch=async()=>({ok:false,status:404});
 await ctx.download([{id:1,name:'Song 01'}]);
 assert(calls.some(x=>x.includes('Saved 0 of 1')));
});
