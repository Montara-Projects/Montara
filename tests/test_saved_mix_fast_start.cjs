/* The saved MP3 must be completely verified before play: MSE fragmented MP3
 * used to play briefly and then fail to decode in Chrome.
 */
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const {test}=require('node:test');
const source=fs.readFileSync(__dirname+'/../web/full-session.js','utf8');
const body=source.slice(source.indexOf('async function playSavedSongMix('),
  source.indexOf('\nfunction warmSessionAudio()'));
test('saved song MP3 downloads verified ranges in parallel and plays only when complete',async()=>{
  let played=0, ranges=[], releaseRemainder;
  const gate=new Promise(resolve=>releaseRemainder=resolve);
  const status={textContent:''};
  const button={textContent:'',classList:{add(){},remove(){}}};
  const sessionPlayer={generation:0,index:-1,controllers:new Set(),urls:new Set(),audio:null};
  const total=5*1024*1024+17;
  const fetch=async(_url,{headers})=>{
    const m=/bytes=(\d+)-(\d+)/.exec(headers.Range),start=+m[1],end=Math.min(+m[2],total-1);
    ranges.push(start);
    if(start>0)await gate;
    return {status:206,headers:{get(name){
      if(name==='Content-Type')return 'audio/mpeg';
      if(name==='Content-Range')return 'bytes '+start+'-'+end+'/'+total;
      return null;
    }},arrayBuffer:async()=>new ArrayBuffer(end-start+1)};
  };
  const urls=new Map();
  class Audio extends EventTarget{
    constructor(url){super();this.url=url;this.readyState=1;this.currentTime=0;}
    async play(){played++;}
    pause(){}
  }
  const session={id:'a'.repeat(12)};
  const ctx={
    fullSession:session,
    sessionPlayer,Audio,URL:{
      createObjectURL(blob){urls.set('blob:song',blob);return 'blob:song';},
      revokeObjectURL(){}
    },fetch,Blob,AbortController,EventTarget,Event,
    document:{querySelector:q=>q.includes('data-song-play')?button:null},
    songList:()=>[{id:3,start:0,end:120}],
    api:async()=>({status:'ready',source:'session-preview'}),
    stopSongPreview:()=>{sessionPlayer.generation++;sessionPlayer.index=-1;},
    '$':()=>status,toast:()=>{},songView:()=>({from:0,to:120}),
    requestAnimationFrame:()=>0,cancelAnimationFrame:()=>{},setTimeout
  };
  vm.createContext(ctx);
  vm.runInContext(body+'\nthis.playSavedSongMix=playSavedSongMix;',ctx);
  const task=ctx.playSavedSongMix(0);
  await new Promise(resolve=>setTimeout(resolve,10));
  assert.equal(played,0,'must not play partial MP3');
  assert.deepEqual(ranges.slice(0,3),[0,2097152,4194304],
    'after the first range, download remaining parts concurrently');
  releaseRemainder();
  await task;
  assert.equal(played,1);
  assert.equal(urls.get('blob:song').size,total);
  assert.equal(sessionPlayer.audio.url,'blob:song');
});
