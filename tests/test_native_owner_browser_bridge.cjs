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
  const document = {
    getElementById:id => id==='footage'?footage:null,
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
  console.log('H3_NATIVE_BROWSER_BRIDGE_PASS startup-lazy, csrf, owner-worker, secured-audio-blob, full-session-review-download');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
