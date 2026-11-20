/* Saved-mix preview must start before the entire MP3 is fetched.
 * This test runs the real browser function against an isolated MediaSource shim.
 */
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const {test}=require('node:test');
const source=fs.readFileSync(__dirname+'/../web/full-session.js','utf8');
const body=source.slice(source.indexOf('async function playSavedSongMix('),
  source.indexOf('\nfunction warmSessionAudio()'));
assert(body.startsWith('async function playSavedSongMix'));
test('saved full DSP mix starts on first 256 KiB and streams remaining bytes',async()=>{
  let played=0, fetched=[], releaseSecond;
  const notices=[];
  const secondGate=new Promise(resolve=>releaseSecond=resolve);
  const status={textContent:''};
  const button={textContent:'',classList:{add(){},remove(){}}};
  const sessionPlayer={generation:0,index:-1,controllers:new Set(),urls:new Set(),audio:null};
  class MediaSource extends EventTarget{
    static isTypeSupported(type){return type==='audio/mpeg';}
    readyState='closed';
    addSourceBuffer(type){
      assert.equal(type,'audio/mpeg');
      return {
        updating:false,
        listeners:new Map(),
        addEventListener(name,fn){this.listeners.set(name,fn);},
        removeEventListener(name,fn){if(this.listeners.get(name)===fn)this.listeners.delete(name);},
        appendBuffer(bytes){
          assert(bytes.byteLength>0);
          queueMicrotask(()=>this.listeners.get('updateend')?.());
        }
      };
    }
    endOfStream(){this.readyState='ended';}
  }
  const instances=[];
  class Audio extends EventTarget{
    constructor(url){super();this.url=url;this.readyState=0;this.currentTime=0;this.paused=true;instances.push(this);}
    load(){
      queueMicrotask(()=>{media.readyState='open';media.dispatchEvent(new Event('sourceopen'));});
    }
    async play(){played++;this.paused=false;}
    pause(){this.paused=true;}
  }
  let media;
  const OriginalMediaSource=MediaSource;
  const createMedia=class extends OriginalMediaSource{
    constructor(){super();media=this;}
  };
  const URLMock={createObjectURL:()=> 'blob:saved-mix', revokeObjectURL(){}};
  const fullSession={id:'a'.repeat(12)};
  const song={id:3,start:0,end:120};
  const total=3*1024*1024;
  const fetch=async(_url,{headers})=>{
    const match=/bytes=(\d+)-(\d+)/.exec(headers.Range);
    const start=+match[1],end=Math.min(+match[2],total-1);
    fetched.push({start,end});
    if(start>0)await secondGate;
    return {status:206,headers:{get(name){
      if(name==='Content-Type')return 'audio/mpeg';
      if(name==='Content-Range')return 'bytes '+start+'-'+end+'/'+total;
      return null;
    }},arrayBuffer:async()=>new ArrayBuffer(end-start+1)};
  };
  const context={
    fullSession,sessionPlayer,MediaSource:createMedia,Audio,URL:URLMock,fetch,
    AbortController,EventTarget,Event,console,
    document:{querySelector:(q)=>q.includes('data-song-play')?button:null},
    songList:()=>[song],
    api:async()=>({status:'ready',source:'session-preview'}),
    stopSongPreview:()=>{
      sessionPlayer.generation++;
      for(const c of sessionPlayer.controllers)c.abort();
      sessionPlayer.controllers=new Set();
      sessionPlayer.index=-1;
    },
    '$':()=>status,toast:(...args)=>notices.push(args),
    songView:()=>({from:0,to:120}),
    requestAnimationFrame:()=>0,
    cancelAnimationFrame:()=>{},
    setTimeout,clearTimeout
  };
  vm.createContext(context);
  vm.runInContext(body+'\nthis.playSavedSongMix=playSavedSongMix;',context);
  await context.playSavedSongMix(0);
  assert.equal(played,1,'audio must play before remainder download finishes');
  assert.equal(fetched[0].start,0);
  assert.equal(fetched[0].end,256*1024-1);
  assert(fetched.length>=2,'remaining chunks should start downloading');
  assert(!instances[0].paused);
  releaseSecond();
  await new Promise(resolve=>setTimeout(resolve,10));
  assert.equal(media.readyState,'ended','media stream should complete '+JSON.stringify({fetched,notices}));
});
