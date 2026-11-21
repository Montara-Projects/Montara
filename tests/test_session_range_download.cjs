'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const src=fs.readFileSync(__dirname+'/../web/full-session.js','utf8');
const begin=src.indexOf('async function getSessionMasterBlob('),end=src.indexOf('async function chooseSessionDownloadDestination(',begin);
assert(begin>0&&end>begin);
const prefix=src.slice(begin,end);
const ctx={
 fullSession:{id:'a'.repeat(12)},
 $:()=>({textContent:''}),
 Blob,Error,Set,Number,Math,Promise,console,
 fetch:async()=>{throw Error('uninitialized');}
};
vm.createContext(ctx);vm.runInContext(prefix+';globalThis.load=getSessionMasterBlob;',ctx);
test('single MP3 transfer uses strict 206 with one megabyte range and validates size',async()=>{
 const expected=Buffer.from('ID3-verified-file');let count=0;
 ctx.fetch=async(path,init)=>{
   assert(path.endsWith('/result/3?download=1'));
   assert.equal(init.headers.Range,'bytes=0-1048575');count++;
   return {status:206,headers:{get:k=>k==='Content-Type'?'audio/mpeg':k==='Content-Range'?'bytes 0-'+(expected.length-1)+'/'+expected.length:null},arrayBuffer:async()=>Uint8Array.from(expected).buffer};
 };
 const blob=await ctx.load({id:3,name:'Song'},'a'.repeat(12));
 assert.equal(blob.size,expected.length);assert.equal(count,1);
});
test('partial or unverified range cannot be written as finished MP3',async()=>{
 ctx.fetch=async()=>({status:206,headers:{get:k=>k==='Content-Type'?'audio/mpeg':k==='Content-Range'?'bytes 0-12/13':null},arrayBuffer:async()=>new Uint8Array(5).buffer});
 await assert.rejects(ctx.load({id:3,name:'Song'},'a'.repeat(12)),/incomplete/);
});
