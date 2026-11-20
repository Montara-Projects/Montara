/* H3: native Chema browser bridge is tested without jsdom or a second UI.
 * Node's built-in VM supplies only the actual browser primitives it needs.
 */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

async function main() {
  const source = fs.readFileSync(
    path.join(__dirname,'../urano/native_owner_browser_bridge.js'),'utf8');
  const calls = [];
  const csrf = 'a'.repeat(64);
  const footage = {hidden:true};
  let observed = null;
  class FakeObserver {
    constructor(callback) { this.callback=callback; }
    observe(target, options) {
      assert.equal(target,footage);
      assert.deepEqual(Array.from(options.attributeFilter),['hidden']);
      observed=this.callback;
    }
    disconnect() {observed=null;}
  }

  async function network(url,options={}) {
    calls.push({url,options});
    if(url==='/urano/v1/session/refresh') {
      return new Response(JSON.stringify({csrf}),{
        status:200,headers:{'Content-Type':'application/json'}});
    }
    if(url==='/urano/v1/native/ensure') {
      return new Response(JSON.stringify({state:'ready',generation:4}),{
        status:200,headers:{'Content-Type':'application/json'}});
    }
    if(url==='/urano/v1/native/rpc/montara/recovery/latest') {
      return new Response(JSON.stringify({error:'No saved project'}),{
        status:404,headers:{'Content-Type':'application/json'}});
    }
    if(url==='/urano/v1/native/rpc/api/v1/wizard/projects/new') {
      return new Response(JSON.stringify({ok:true}),{
        status:200,headers:{'Content-Type':'application/json',
                            'X-Montara-Engine-Generation':'4'}});
    }
    if(url==='/urano/v1/native/rpc/api/v1/wizard/review?render=0') {
      return new Response(JSON.stringify({
        items:[{index:0,
          thumbnail:'/api/v1/wizard/review/thumbnail/assets-v2/frame-0.jpg',
          preview:'/api/v1/wizard/review/preview/0?v=123abc'}],
        platform:'youtube'
      }),{status:200,headers:{'Content-Type':'application/json'}});
    }
    if(url==='/urano/v1/native/rpc/api/v1/wizard/review/thumbnail/assets-v2/frame-0.jpg') {
      return new Response(new Uint8Array([255,216,255,217]),{
        status:200,headers:{'Content-Type':'image/jpeg'}});
    }
    if(url.startsWith('/urano/v1/native/rpc/montara/audio?path=')) {
      return new Response(new Uint8Array([82,73,70,70,0,0,0,0]),{
        status:200,headers:{'Content-Type':'audio/x-wav'}});
    }
    if(url==='/urano/v1/native/rpc/montara/branding') {
      return new Response(JSON.stringify({mode:'montara',has_logo:false}),{
        status:200,headers:{'Content-Type':'application/json'}});
    }
    if(url.startsWith('/urano/v1/native/rpc/api/v1/edit/native-recipe?')) {
      return new Response(JSON.stringify({version:1,engine:'a'.repeat(40),
        revision:'a'.repeat(20),sources:[],segments:[]}),
        {status:200,headers:{'Content-Type':'application/json'}});
    }
    if(url.startsWith('/urano/v1/native/rpc/api/v1/edit/native-master?')) {
      return new Response(new Uint8Array([82,73,70,70]),
        {status:200,headers:{'Content-Type':'audio/x-wav'}});
    }
    if(url.startsWith('/urano/v1/native/rpc/api/v1/edit/native-source/0?')) {
      return new Response(options.method==='HEAD'?null:
        new Uint8Array([0,0,0,1]),{
        status:200,headers:{'Content-Type':'video/mp4'}});
    }
    if(url==='/urano/v1/native/rpc/api/v1/edit/shot?index=3') {
      return new Response(JSON.stringify({index:3,revision:'a'.repeat(20)}),
        {status:200,headers:{'Content-Type':'application/json'}});
    }
    if(url==='/urano/v1/native/rpc/api/v1/edit/shot/save') {
      return new Response(JSON.stringify({ok:true}),
        {status:200,headers:{'Content-Type':'application/json'}});
    }
    if(url==='/urano/v1/native/rpc/api/v1/edit/shot/frame?index=3&choice=0&revision='+('a'.repeat(20))) {
      return new Response(new Uint8Array([255,216,255,217]),
        {status:200,headers:{'Content-Type':'image/jpeg'}});
    }
    const manyUpload=url.match(/^\/urano\/v1\/native\/rpc\/montara\/uploads\/(0{30}[0-9a-e]{2})\/finish$/);
    if(manyUpload) {
      const id=manyUpload[1], num=parseInt(id.slice(-2),16), filename='Audio-'+String(num).padStart(2,'0')+'.wav';
      return new Response(JSON.stringify({master:[{
        kind:'master',filename,path:'/private-current/Uploads/'+id+'/'+filename,
        duration:120,checked:true
      }],songs:[],videos:[],ignored:[]}),{
        status:200,headers:{'Content-Type':'application/json'}});
    }
    if(url==='/urano/v1/native/rpc/montara/uploads/'+'c'.repeat(32)+'/finish') {
      assert.equal(options.method,'POST');
      return new Response(JSON.stringify({master:[{
        kind:'master',filename:'source.wav',
        path:'/fresh-private/Uploads/'+'c'.repeat(32)+'/source.wav'
      }],songs:[],ignored:[],videos:[]}),{status:200,headers:{'Content-Type':'application/json'}});
    }
    if(url==='/urano/v1/native/rpc/montara/uploads/'+'d'.repeat(32)+'/finish') {
      assert.equal(options.method,'POST');
      // 15 real JM audio files were uploaded as .opus and restored to .wav.
      // The original browser code wrongly insisted on identical filenames.
      return new Response(JSON.stringify({master:[{
        kind:'master',filename:'different-track.wav',
        path:'/owner-current/Uploads/'+'d'.repeat(32)+'/different-track.wav'
      }]}),{status:200,headers:{'Content-Type':'application/json'}});
    }
    if(url==='/urano/v1/native/rpc/montara/uploads/'+'e'.repeat(32)+'/finish') {
      return new Response(JSON.stringify({songs:[],master:[]}),{
        status:200,headers:{'Content-Type':'application/json'}});
    }
    if(url==='/urano/v1/native/rpc/montara/uploads/'+'f'.repeat(32)+'/finish') {
      return new Response(JSON.stringify({master:[{
        kind:'master',filename:'different-track.wav',
        path:'/owner-current/Uploads/'+'f'.repeat(32)+'/different-track.wav'
      }]}),{status:200,headers:{'Content-Type':'application/json'}});
    }
    if (url==='/urano/v1/native/rpc/montara/session') {
      assert.equal(options.method,'POST');
      return new Response(JSON.stringify({id:'a'.repeat(12),status:'detecting'}),{
        status:202,headers:{'Content-Type':'application/json'}});
    }
    if (url==='/urano/v1/native/rpc/montara/session/'+'a'.repeat(12)) {
      return new Response(JSON.stringify({id:'a'.repeat(12),status:'ready',
        songs:[{id:1,start:0,end:20,selected:true}]}),{
        status:200,headers:{'Content-Type':'application/json'}});
    }
    if(url==='/urano/v1/native/rpc/montara/session/'+'a'.repeat(12)+'/listen') {
      return new Response(options.method==='HEAD'?null:new Uint8Array([26,69,223,163]),{
        status:200,headers:{'Content-Type':'audio/webm'}});
    }
    if(url==='/urano/v1/native/rpc/montara/session/'+'a'.repeat(12)+'/waveform') {
      return new Response(JSON.stringify({step:.25,peaks:[1,2]}),{
        status:200,headers:{'Content-Type':'application/json'}});
    }
    if(url==='/urano/v1/native/rpc/montara/session/'+'a'.repeat(12)+'/result/1?download=1') {
      return new Response(new Uint8Array([73,68,51]),{status:200,
        headers:{'Content-Type':'audio/mpeg'}});
    }
    if(url==='/urano/v1/native/rpc/montara/session/'+'a'.repeat(12)+'/results.zip') {
      return new Response(new Uint8Array([80,75,3,4]),{status:200,
        headers:{'Content-Type':'application/zip'}});
    }
    if(url==='/urano/v1/native/rpc/montara/companion/version') {
      return new Response(JSON.stringify({engine:'e'.repeat(40),
        installer_available:true,
        download:'/urano/v1/native/companion/download'}),{
          status:200,headers:{'Content-Type':'application/json'}});
    }
    if(url==='/montara/companion/version') {
      return new Response(JSON.stringify({version:'0.6.5'}),{status:200});
    }
    throw Error('Unexpected real network call '+url);
  }

  class FakeMediaElement {
    constructor() {this._src='';this.loaded=false;}
    load(){this.loaded=true;}
    dispatchEvent(){}
  }
  Object.defineProperty(FakeMediaElement.prototype,'src',{
    configurable:true,get(){return this._src;},set(v){this._src=v;}
  });
  class FakeAudioElement extends FakeMediaElement {}
  class FakeImageElement extends FakeMediaElement {}
  Object.defineProperty(FakeImageElement.prototype,'src',{
    configurable:true,get(){return this._src;},set(v){this._src=v;}
  });
  const window = {fetch:network,Audio:FakeAudioElement};
  const listeners = {};
  const downloads = [];
  const sampleHint={textContent:''};
  const companionLink={href:'/montara/companion/download',hidden:false,
    setAttribute(key,value){if(key==='href')this.href=value;},
    removeAttribute(key){if(key==='href')this.href='';}};
  const document = {
    getElementById:id => id==='footage'?footage:
      id==='footageHint'?sampleHint:
      id==='companionUpdateDownload'?companionLink:null,
    addEventListener:(type,callback) => {listeners[type]=callback;},
    createElement:tag => {
      assert.equal(tag,'a');
      const node={href:'',download:'',
        click(){downloads.push({href:this.href,filename:this.download});}};
      return node;
    },
  };
  const context = {
    window, location:{
      origin:'https://montara.test',
      href:'https://montara.test/urano/v1/native/'
    },
    document,
    MutationObserver:FakeObserver,URL,Response,Headers,
    setTimeout:(fn)=>{fn(); return 1;},
    XMLHttpRequest:undefined,
    HTMLMediaElement:FakeMediaElement,HTMLAudioElement:FakeAudioElement,
    HTMLImageElement:FakeImageElement,
  };
  vm.runInNewContext(source,context,{filename:'native_owner_browser_bridge.js'});
  assert.equal(typeof window.fetch,'function');

  // Chema calls Latest on startup: neither Google CSRF nor the Engine may
  // be contacted until Chema itself shows its original Footage/Stage screen.
  const startup = window.fetch('/montara/recovery/latest');
  await Promise.resolve();
  assert.equal(calls.length,0);
  assert.equal(typeof observed,'function');

  // Original Home version is a lightweight local label, not an Engine start.
  const version=await window.fetch('/montara/version');
  assert.equal(version.status,200);
  assert.equal(calls.length,0);

  footage.hidden=false;
  observed();
  const latest=await startup;
  assert.equal(latest.status,404);
  assert.deepEqual(calls.map(c=>c.url),[
    '/urano/v1/session/refresh','/urano/v1/native/ensure',
    '/urano/v1/native/rpc/montara/recovery/latest']);
  assert.equal(calls[2].options.headers.get('X-Urano-CSRF'),csrf);
  assert.equal(calls[2].options.headers.get('X-Montara-Engine-Generation'),'4');

  // GET samples is explicitly disabled in an Owner lab without its own
  // fixture catalog. It must explain the limitation, not throw or leak paths.
  const countBeforeSamples=calls.length;
  const samples=await window.fetch('/montara/samples?platform=youtube&variant=');
  assert.equal(samples.status,200);
  assert.equal((await samples.json()).enabled,false);
  assert.match(sampleHint.textContent,/Example media/);
  assert.equal(calls.length,countBeforeSamples);
  await assert.rejects(
    ()=>window.fetch('/montara/samples?platform=youtube&variant=&path=/etc/passwd'),
    /not enabled/);
  const companionMetadata=await window.fetch('/montara/companion/version');
  assert.equal(companionMetadata.status,200);
  const companionInfo=await companionMetadata.json();
  assert.equal(companionInfo.engine,'e'.repeat(40));
  assert.equal(companionInfo.installer_available,true);
  assert.equal(companionInfo.download,'/urano/v1/native/companion/download');
  assert.equal(companionLink.hidden,false);
  assert.equal(companionLink.href,'/urano/v1/native/companion/download');
  assert.equal(calls.at(-1).url,
    '/urano/v1/native/rpc/montara/companion/version');
  assert.equal(calls.at(-1).options.headers.get('X-Urano-CSRF'),csrf);
  calls.pop(); // keep previous scenario's fixed request index assertions stable

  const created=await window.fetch('/api/v1/wizard/projects/new',{
    method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
  assert.equal(created.status,200);
  assert.equal(calls.length,4); // same worker and same rotating CSRF
  assert.equal(calls[3].url,
    '/urano/v1/native/rpc/api/v1/wizard/projects/new');
  assert.equal(calls[3].options.method,'POST');

  const review=await window.fetch('/api/v1/wizard/review?render=0');
  assert.equal(review.status,200);
  const reviewResult=await review.json();
  assert.ok(reviewResult.items[0].thumbnail.startsWith('blob:'));
  assert.equal(calls[4].url,
    '/urano/v1/native/rpc/api/v1/wizard/review?render=0');
  assert.equal(calls[5].url,
    '/urano/v1/native/rpc/api/v1/wizard/review/thumbnail/assets-v2/frame-0.jpg');
  const project='/private/Projects/test.zuckervid';
  const recipeUrl='/api/v1/edit/native-recipe?project_id='+encodeURIComponent(project);
  const mediaQuery=new URLSearchParams({project_id:project,revision:'a'.repeat(20)});
  const recipe=await window.fetch(recipeUrl);
  assert.equal(recipe.status,200);
  assert.equal((await recipe.json()).engine,'a'.repeat(40));
  const master=await window.fetch('/api/v1/edit/native-master?'+mediaQuery);
  assert.equal(master.status,200);
  assert.equal((await master.blob()).size,4);
  const sourceCheck=await window.fetch('/api/v1/edit/native-source/0?'+mediaQuery,
    {method:'HEAD'});
  assert.equal(sourceCheck.status,200);
  assert.equal(calls.at(-1).options.method,'HEAD');
  for(const c of calls.slice(-3))
    assert.equal(c.options.headers.get('X-Urano-CSRF'),csrf);
  const framePath='/api/v1/edit/shot/frame?index=3&choice=0&revision='+('a'.repeat(20));
  const shot=await window.fetch('/api/v1/edit/shot?index=3');
  assert.equal(shot.status,200);
  assert.equal((await shot.json()).index,3);
  const shotPatch=await window.fetch('/api/v1/edit/shot',{
    method:'PATCH',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({project_id:'/owner/Projects/test',revision:'a'.repeat(20),
      index:3,choice:0,apply_to_source:false,edit_component:'movement'})
  });
  assert.equal(shotPatch.status,200);
  const patchWire=calls.at(-1);
  assert.equal(patchWire.url,'/urano/v1/native/rpc/api/v1/edit/shot/save');
  assert.equal(patchWire.options.method,'POST');
  assert.equal(patchWire.options.headers.has('X-Montara-Shot-Method'),false);
  assert.equal(patchWire.options.headers.get('X-Urano-CSRF'),csrf);
  const image=new FakeImageElement();
  image.src=framePath;
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(image._src.startsWith('blob:'),image._src);
  assert.equal(image.src,framePath);
  assert.equal(calls.at(-1).url,'/urano/v1/native/rpc/'+framePath.slice(1));
  const branding=await window.fetch('/montara/branding',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({mode:'montara'})
  });
  assert.equal(branding.status,200);
  assert.equal(calls.at(-1).url,'/urano/v1/native/rpc/montara/branding');
  assert.equal(calls.at(-1).options.headers.get('X-Urano-CSRF'),csrf);
  assert.equal(calls.at(-1).options.headers.get('X-Montara-Engine-Generation'),'4');

  await assert.rejects(
    () => window.fetch('/api/v1/internal/other'),
    /not enabled/);
  await assert.rejects(
    () => window.fetch('/montara/session/secret'),
    /not enabled/);
  assert.equal(calls.length,13);
  const sound = new FakeAudioElement();
  sound.src='/montara/audio?path='+encodeURIComponent('/private/WizardUploads/song.wav');
  await new Promise(resolve=>setTimeout(resolve,30));
  assert.ok(sound.loaded,'Original song player must load its private audio blob');
  assert.ok(sound._src.startsWith('blob:'),'Audio bytes must use a browser-local blob');
  assert.equal(calls.at(-1).url,'/urano/v1/native/rpc/montara/audio?path='+encodeURIComponent('/private/WizardUploads/song.wav'));
  assert.equal(calls.at(-1).options.headers.get('X-Urano-CSRF'),csrf);
  const sessionId='a'.repeat(12);
  const session=await window.fetch('/montara/session',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({tracks:['/private/test.wav'],for_video:false})});
  assert.equal(session.status,202);
  assert.equal((await session.json()).id,sessionId);
  const sessionSent=calls.at(-1);
  assert.equal(sessionSent.url,'/urano/v1/native/rpc/montara/session');
  assert.equal(sessionSent.options.headers.get('X-Urano-CSRF'),csrf);
  const state=await window.fetch('/montara/session/'+sessionId);
  assert.equal((await state.json()).songs[0].id,1);
  const wave=await window.fetch('/montara/session/'+sessionId+'/waveform');
  assert.equal((await wave.json()).peaks.length,2);
  const listenHead=await window.fetch('/montara/session/'+sessionId+'/listen',{method:'HEAD'});
  assert.equal(listenHead.status,200);
  assert.equal(calls.at(-1).options.method,'HEAD');
  const listen=new FakeAudioElement();
  listen.src='/montara/session/'+sessionId+'/listen';
  await new Promise(resolve=>setTimeout(resolve,30));
  assert.ok(listen.loaded);
  assert.ok(listen._src.startsWith('blob:'));
  assert.equal(listen.src,'/montara/session/'+sessionId+'/listen');
  // Real Chema uses new Audio(url), not audio.src=url. Native constructors
  // bypass the setter; the Owner adapter must keep this path authenticated.
  const constructed = new window.Audio('/montara/session/'+sessionId+'/listen');
  assert.ok(constructed instanceof FakeAudioElement);
  await new Promise(resolve=>setTimeout(resolve,30));
  assert.ok(constructed.loaded,'new Audio(url) should load the private blob');
  assert.ok(constructed._src.startsWith('blob:'));
  assert.equal(constructed.src,'/montara/session/'+sessionId+'/listen');
  assert.equal(calls.at(-1).url,
    '/urano/v1/native/rpc/montara/session/'+sessionId+'/listen');
  for(const invalid of [
    '/montara/session/'+sessionId+'/admin',
    '/montara/session/'+sessionId+'/result/2?download=0',
    '/montara/session/'+sessionId+'/listen?start=-1&end=30',
    '/montara/session/'+sessionId+'/originals?song=1&path=/etc/passwd',
  ]) await assert.rejects(()=>window.fetch(invalid),/not enabled/);
  assert.equal(calls.at(-1).url,'/urano/v1/native/rpc/montara/session/'+sessionId+'/listen');

  assert.equal(typeof listeners.click,'function','Session links must be intercepted');
  const clickLink = async href => {
    let prevented=false;
    listeners.click({
      target:{closest:()=>({getAttribute:key=>key==='href'?href:null})},
      preventDefault(){prevented=true;}
    });
    await new Promise(resolve=>setImmediate(resolve));
    assert.ok(prevented,'Private download must never navigate to /montara/session');
    return calls.at(-1);
  };
  const songDownload=await clickLink('/montara/session/'+sessionId+'/result/1?download=1');
  assert.equal(songDownload.url,'/urano/v1/native/rpc/montara/session/'+sessionId+'/result/1?download=1');
  assert.ok(downloads.at(-1).href.startsWith('blob:'));
  assert.equal(downloads.at(-1).filename,'Montara-song.mp3');
  const zipDownload=await clickLink('/montara/session/'+sessionId+'/results.zip');
  assert.equal(zipDownload.url,'/urano/v1/native/rpc/montara/session/'+sessionId+'/results.zip');
  assert.equal(downloads.at(-1).filename,'Montara-session.zip');
  // A restored browser record may contain an obsolete absolute path after
  // the Owner worker moved. Idempotent /finish resolves only a completed
  // current-owner upload: no local video recreation, no new bytes sent.
  const upload='c'.repeat(32);
  const stale='/old-data/Uploads/'+upload+'/source.wav';
  const canonical='/fresh-private/Uploads/'+upload+'/source.wav';
  const recovered=await window.fetch('/montara/session',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({tracks:[stale,stale],for_video:false})
  });
  assert.equal(recovered.status,202);
  const reconciledWire=calls.at(-1);
  assert.equal(reconciledWire.url,'/urano/v1/native/rpc/montara/session');
  assert.deepEqual(JSON.parse(reconciledWire.options.body).tracks,[canonical]);
  assert.equal(reconciledWire.options.headers.get('X-Urano-CSRF'),csrf);
  assert.equal(calls.filter(call=>call.url.endsWith('/uploads/'+upload+'/finish')).length,1);
  assert.equal(calls.find(call=>call.url.endsWith('/uploads/'+upload+'/finish'))
    .options.headers.get('X-Urano-CSRF'),csrf);
  const again=await window.fetch('/montara/session',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({tracks:[stale],for_video:false})
  });
  assert.equal(again.status,202);
  assert.equal(calls.filter(call=>call.url.endsWith('/uploads/'+upload+'/finish')).length,1,
    'Reconciliation should reuse current-owner completed upload metadata');
  const opus='d'.repeat(32);
  const opusOld='/owner-before/Uploads/'+opus+'/different-track.wav.opus';
  const opusResolved='/owner-current/Uploads/'+opus+'/different-track.wav';
  const opusSession=await window.fetch('/montara/session',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({tracks:[opusOld,opusOld],for_video:false})
  });
  assert.equal(opusSession.status,202);
  assert.deepEqual(JSON.parse(calls.at(-1).options.body).tracks,[opusResolved]);
  assert.equal(calls.filter(c=>c.url.endsWith('/uploads/'+opus+'/finish')).length,1);
  const posts=calls.filter(c=>c.url==='/urano/v1/native/rpc/montara/session').length;
  // An Owner worker that does not return a verified restored file must never
  // receive an unverified session body. The original UI sees a meaningful 409,
  // not "Lost connection" from a thrown fetch.
  const missing=await window.fetch('/montara/session',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({tracks:['/old/Uploads/'+'e'.repeat(32)+'/missing.wav.opus']})
  });
  assert.equal(missing.status,409);
  assert.match((await missing.json()).error.message,/Cannot verify/);
  assert.equal(calls.filter(c=>c.url==='/urano/v1/native/rpc/montara/session').length,posts);
  // Two different sources with the same basename must not be silently lost.
  const nameCollision=await window.fetch('/montara/session',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({tracks:[
      opusOld,
      '/old/Uploads/'+'f'.repeat(32)+'/different-track.wav.opus'
    ]})
  });
  assert.equal(nameCollision.status,409);
  assert.match((await nameCollision.json()).error.message,/same filename/);
  assert.equal(calls.filter(c=>c.url==='/urano/v1/native/rpc/montara/session').length,posts);
  // The actual Engine's inbox classifier emits master[].filename, never
  // master[].name. Regress all 15 existing LAB JM Opus -> WAV tracks.
  const fifteenIds=Array.from({length:15},(_,n)=>'0'.repeat(30)+n.toString(16).padStart(2,'0'));
  const fifteenOld=fifteenIds.map((id,n)=>'/stale/Uploads/'+id+'/Audio-'+String(n).padStart(2,'0')+'.wav.opus');
  const before15=calls.filter(c=>c.url==='/urano/v1/native/rpc/montara/session').length;
  const fifteen=await window.fetch('/montara/session',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({tracks:fifteenOld,track_types:{},for_video:false})
  });
  assert.equal(fifteen.status,202);
  const fifteenWire=JSON.parse(calls.at(-1).options.body);
  assert.equal(fifteenWire.tracks.length,15);
  assert.deepEqual(fifteenWire.tracks,fifteenIds.map((id,n)=>
    '/private-current/Uploads/'+id+'/Audio-'+String(n).padStart(2,'0')+'.wav'));
  assert.equal(calls.filter(c=>c.url==='/urano/v1/native/rpc/montara/session').length,before15+1);
  for (const id of fifteenIds)
    assert.equal(calls.filter(c=>c.url.endsWith('/uploads/'+id+'/finish')).length,1);
  console.log('H3_NATIVE_BROWSER_BRIDGE_PASS real Engine master[].filename contract, 15 Opus-to-WAV, CSRF, isolation, playback, downloads, collision-guard');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
