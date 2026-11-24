/* Real Chema LAB-JM song-review playback regression.
 * Executes exactly the edited functions from full-session.js; no second UI.
 */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(__dirname+'/../web/full-session.js','utf8');
const start=source.indexOf('const SONG_LISTEN_CHUNK_SECONDS =');
const end=source.indexOf('// Click on a waveform (not on a handle)',start);
assert(start>0 && end>start);
const snippet=source.slice(start,end);
const calls=[];
const songs=[{start:0,end:64},{start:64,end:1641.5}];
const sessionPlayer={audio:null,index:-1,raf:0};
const state={sessionStatus:{textContent:''}};
const button={classList:{add(){},remove(){}},textContent:''};
const head={hidden:true,style:{}};
const row={clientWidth:450,querySelector:s=>s==='.song-playhead'?head:null};
const revoked=new Set();
const allAudio=[];
let errorStatus=null;
class FakeAudio {
  constructor(src){this.src=src;this.currentTime=0;this.listeners={};allAudio.push(this);}
  addEventListener(type,fn){this.listeners[type]=fn;}
  load(){this.loaded=true;}
  pause(){this.paused=true;}
  async play(){this.played=true;}
}
const context={
  sessionPlayer,
  fullSession:{id:'a'.repeat(12),data:{songs}},
  songList:()=>songs,
  $:id=>state[id.slice(1)] || state.sessionStatus,
  document:{
    querySelector:selector=>selector.includes('data-song-play')?button:selector.includes('data-song-wave')?row:null,
    querySelectorAll:()=>[],
  },
  URL:{createObjectURL:()=>`blob:test/0.6829241718369442`,revokeObjectURL:url=>revoked.add(url)},
  URLSearchParams, Response, Blob, AbortController,
  Audio:FakeAudio,
  fetch:async(url,{method,signal}={})=>{
    calls.push({url,method});
    assert.equal(method,'GET');
    assert(url.startsWith("/montara/session/") && url.includes("/listen?start="));
    if(errorStatus) return new Response(JSON.stringify({error:'failed'}),{status:errorStatus,headers:{'Content-Type':'application/json'}});
    return new Response(new Blob([Buffer.from('OggS')],{type:'audio/ogg'}),{status:200,headers:{'Content-Type':'audio/ogg','Content-Length':'4'}});
  },
  requestAnimationFrame:()=>1,cancelAnimationFrame:()=>{},
  songView:()=>({from:64,to:1650}),
  toast:(message,important)=>{context.error=message;},
  console
};
vm.createContext(context);
vm.runInContext(snippet+';globalThis.__play=playSong;globalThis.__stop=stopSongPreview;globalThis.__warm=warmSessionAudio;',context);
const settled=()=>new Promise(resolve=>setTimeout(resolve,10));
(async()=>{
  context.__warm();
  assert.equal(calls.length,0,'song review must not issue huge whole-session HEAD');
  await context.__play(1);
  assert.equal(sessionPlayer.index,1);
  assert.equal(allAudio[0].played,true);
  assert.equal(calls[0].url,'/montara/session/'+('a'.repeat(12))+'/listen?start=64.00&end=109.00');
  await settled();
  assert.equal(calls[1].url,'/montara/session/'+('a'.repeat(12))+'/listen?start=109.00&end=154.00');
  assert.equal(head.hidden,false);
  allAudio[0].listeners.ended();
  await settled();
  assert.equal(allAudio[1].played,true,'next chunk must start automatically');
  assert.equal(sessionPlayer.index,1);
  assert(calls.every(x=>x.url.includes('?start=')),'no whole-session listening conversion');
  const oldAudio=sessionPlayer.audio;
  await context.__play(1,1000);
  assert.equal(oldAudio.paused,true,'seeking stops previous segment');
  assert.equal(sessionPlayer.index,1);
  assert(calls.some(x=>x.url.includes('start=1000.00&end=1045.00')));
  context.__stop();
  assert.equal(sessionPlayer.index,-1);
  assert(revoked.size>0,'preview object URLs are revoked');
  errorStatus=503;
  await context.__play(0);
  assert.equal(sessionPlayer.index,-1);
  assert.match(context.error,/503/);
  assert(calls.every(x=>x.url.includes('?start=')));
  console.log('JM_FULL_SESSION_CHUNK_PLAYBACK_TEST_PASS no_full_HEAD, 45s_chunk, advance, seek, cleanup, error');
})().catch(e=>{console.error(e);process.exitCode=1;});