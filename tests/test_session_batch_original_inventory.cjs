'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const src=fs.readFileSync(__dirname+'/../web/full-session.js','utf8');
const begin=src.indexOf('async function queueAllSongOriginals(');
const end=src.indexOf('async function queueSongOriginals(song)',begin);
assert(begin>0&&end>begin);
test('30 songs use one authenticated inventory request, preserving received ranges',async()=>{
  let calls=0,started=0;
  const songs=Array.from({length:30},(_,i)=>({id:i+1,start:i*10,end:(i+1)*10}));
  const all=songs.map(song=>({song:song.id,original:{name:'test.wav'},file:'test.wav',
    window:[song.start,song.end],start:song.start,duration:10,received:song.id<=2}));
  const up={queue:[],seen:new Set(),done:0,total:0,byWindow:{},running:false};
  const ctx={
    fullSession:{id:'a'.repeat(12)},uploader:up,checkSessionCancel:()=>{},
    api:async path=>{calls++;assert.equal(path,'/montara/session/'+('a'.repeat(12))+'/originals');return {originals:all};},
    windowKey:s=>Number(s.start).toFixed(3)+'-'+Number(s.end).toFixed(3),
    $:()=>({textContent:''}),paintUploadState:()=>{},runUploader:()=>{started++},
    setTimeout
  };
  vm.createContext(ctx);
  vm.runInContext(src.slice(begin,end)+';this.batch=queueAllSongOriginals;',ctx);
  await ctx.batch(songs);
  assert.equal(calls,1);
  assert.equal(up.queue.length,28);
  assert.equal(up.total,28);
  assert.equal(Object.keys(up.byWindow).length,30);
  assert.equal(up.byWindow['0.000-10.000'].done,1);
  assert.equal(started,30);
  await ctx.batch(songs);
  assert.equal(up.queue.length,28,'repeat inventory must not duplicate pending ranges');
});
