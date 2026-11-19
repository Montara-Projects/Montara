/* Native Chema Owner adapter.
 * Runs BEFORE Chema's unmodified scripts. No dashboard, catalog or extra UI.
 * A browser never supplies owner_id, workspace UUID, PID, socket or unit.
 * A verified Google session/CSRF selects the workspace at the Owner server;
 * the root broker repeats the identity check for every worker descriptor.
 * Unknown native APIs are blocked, not accidentally sent to a shared Engine.
 */
(() => {
  'use strict';
  const originalFetch = window.fetch.bind(window);
  const routes = new Set([
    'api/v1/wizard/projects', 'api/v1/wizard/projects/new',
    'api/v1/wizard/projects/open', 'api/v1/wizard/projects/delete',
    'api/v1/wizard/draft', 'api/v1/wizard/prepare', 'api/v1/wizard/start',
    'api/v1/wizard/cancel', 'api/v1/wizard/status',
    'api/v1/project', 'montara/recovery/latest',
    'api/v1/artifacts/sync',
    'api/v1/wizard/review', 'api/v1/wizard/review/replace',
    'api/v1/wizard/review/render',
    'api/v1/wizard/upload','montara/uploads','montara/branding',
    'api/v1/edit/shot', 'api/v1/edit/shot/frame',
    'api/v1/edit/native-recipe','api/v1/edit/native-master',
    'api/v1/edit/timeline',
    'api/v1/settings/fillers','api/v1/settings/video-light',
    'api/v1/settings/camera-types','api/v1/settings/camera-subjects',
    'api/v1/settings/camera-roles','api/v1/settings/spherical-landmarks',
    'api/v1/settings/stage-performers'
  ]);
  const nativePrefix = '/urano/v1/native/rpc/';
  let csrfPromise = null;
  let ensurePromise = null;
  let generation = null;

  const token = () => {
    if (!csrfPromise) {
      csrfPromise = originalFetch('/urano/v1/session/refresh', {
        method: 'POST', credentials: 'same-origin', cache: 'no-store',
        headers: { 'Origin': location.origin }
      }).then(async response => {
        if (!response.ok) throw new Error('Montara session expired');
        const value = await response.json();
        if (!/^[a-f0-9]{64}$/.test(value.csrf || ''))
          throw new Error('Montara CSRF unavailable');
        return value.csrf;
      }).catch(error => { csrfPromise = null; throw error; });
    }
    return csrfPromise;
  };

  const ensure = () => {
    if (!ensurePromise) {
      ensurePromise = token().then(async csrf => {
        const response = await originalFetch('/urano/v1/native/ensure', {
          method:'POST', cache:'no-store', credentials:'same-origin',
          headers: { 'X-Urano-CSRF':csrf, 'Origin':location.origin }
        });
        if (!response.ok) {
          const msg = (await response.json().catch(() => ({}))).error;
          throw new Error(typeof msg === 'string' ? msg :
            'Your private Montara workspace is unavailable');
        }
        const value = await response.json();
        if (value.state !== 'ready' ||
            !Number.isSafeInteger(value.generation) ||
            value.generation < 1)
          throw new Error('Private worker verification failed');
        generation = value.generation;
        return generation;
      }).catch(error => { ensurePromise = null; throw error; });
    }
    return ensurePromise;
  };

  // The full-session editor uses these exact endpoints. Unknown Music paths,
  // query formats and methods stay fail-closed at BOTH browser and server.
  const sessionAllowed = (path, method, params) => {
    if (path === '/montara/session')
      return method === 'POST' && params.size === 0;
    if (path === '/montara/session/latest')
      return method === 'GET' && params.size === 0;
    const found = /^\/montara\/session\/([a-f0-9]{12})(?:\/(.*))?$/.exec(path);
    if (!found) return false;
    const suffix = found[2] || '';
    const noQuery = params.size === 0;
    if (method === 'GET' && noQuery &&
        (!suffix || ['video-source','waveform','results.zip'].includes(suffix)))
      return true;
    if (method === 'POST' && noQuery && [
      'cancel','include','prepare','render','songs','video-master',
      'originals','local-result'
    ].includes(suffix)) return true;
    if (suffix === 'listen' && (method === 'GET' || method === 'HEAD')) {
      if (noQuery) return true;
      return method === 'GET' && params.size === 2 &&
        ['start','end'].every(k => params.has(k) && params.getAll(k).length === 1 &&
        /^[0-9]{1,9}(?:\.[0-9]{1,6})?$/.test(params.get(k)));
    }
    if (method !== 'GET') return false;
    if (suffix === 'originals' || suffix === 'local-plan') {
      if (suffix === 'originals' && noQuery) return true;
      if (suffix === 'originals' && params.size === 1 && params.has('song'))
        return /^[1-9][0-9]{0,3}$/.test(params.get('song'));
      return params.size >= 3 && params.size <= 4 &&
        [...params.keys()].every(k => ['song','start','end','name'].includes(k)) &&
        ['song','start','end'].every(k => params.getAll(k).length === 1 &&
          (k === 'song' ? /^[1-9][0-9]{0,3}$/.test(params.get(k)) :
            /^[0-9]{1,9}(?:\.[0-9]{1,6})?$/.test(params.get(k)))) &&
        (!params.has('name') || params.getAll('name').length === 1 &&
          params.get('name').length <= 80);
    }
    if (/^result\/[1-9][0-9]{0,3}$/.test(suffix)) {
      if (noQuery) return true;
      return params.size === 1 &&
        (params.get('download') === '1' && params.getAll('download').length === 1 ||
        /^[0-9]{1,6}$/.test(params.get('v') || '') &&
          params.getAll('v').length === 1);
    }
    return false;
  };

  const route = (input, method = 'GET') => {
    const raw = typeof input === 'string' ? input :
      input instanceof URL ? input.href : input?.url;
    if (typeof raw !== 'string') return null;
    const address = new URL(raw, location.href);
    if (address.origin !== location.origin) return null;
    const p = address.pathname;
    if (!p.startsWith('/api/v1/') && !p.startsWith('/montara/'))
      return null;
    if (p === '/montara/version' && method === 'GET')
      return { kind:'metadata', data:{version:'Montara Owner Beta'} };
    // Real version from this LAB's root-verified Engine pin. Never lie about
    // the installed Mac Companion or offer a nonexistent local installer.
    if (p === '/montara/companion/version' && method === 'GET' &&
        !address.search && !address.hash)
      return {kind:'worker',path:nativePrefix+'montara/companion/version'};
    // Original sample fixtures are not enrolled in private Owner data roots.
    // Fail transparently without offering shared filesystem paths to users.
    if (p === '/montara/samples' && method === 'GET' && !address.hash) {
      const params=address.searchParams;
      if (params.size === 2 && params.has('platform') &&
          params.getAll('platform').length===1 &&
          ['youtube','reel','show'].includes(params.get('platform')) &&
          params.has('variant') && params.getAll('variant').length===1 &&
          /^[a-z0-9_-]{0,32}$/.test(params.get('variant')))
        return {kind:'metadata',sampleUnavailable:true,
                data:{enabled:false,reason:'Example media is not installed in private LAB JM.'}};
      return {kind:'blocked'};
    }
    if (p === '/montara/branding' && method === 'GET')
      return { kind:'metadata', data:{mode:'montara',has_logo:false} };
    const operation = p.substring(1);
    const sessionRoute = sessionAllowed(p,method,address.searchParams);
    const resumable = /^montara\/uploads\/[a-f0-9]{32}(?:\/finish)?$/.test(operation);
    const audioRoute = operation === 'montara/audio' && method === 'GET';
    const nativeSource = /^api\/v1\/edit\/native-source\/[0-9]{1,3}$/.test(
      operation) && (method==='HEAD' || method==='GET');
    const reviewedPreview = /^api\/v1\/wizard\/review\/preview\/[0-9]{1,5}$/.test(operation);
    const reviewedThumbnail = /^api\/v1\/wizard\/review\/thumbnail\/(?:assets-v2|[a-f0-9]{16,128})\/[A-Za-z0-9_.-]{1,180}$/.test(operation);
    if (address.hash || (!routes.has(operation) && !audioRoute && !resumable &&
                         !reviewedPreview && !reviewedThumbnail && !nativeSource &&
                         !sessionRoute))
      return {kind:'blocked'};
    const params = address.searchParams;
    const isStatus = operation === 'api/v1/wizard/status' &&
      params.size === 1 && params.has('project_id') &&
      (params.get('project_id')||'').length <= 4096;
    const review = operation === 'api/v1/wizard/review' &&
      params.size >= 1 && params.size <= 2 &&
      [...params.keys()].every(key => key === 'render' || key === 'shot') &&
      ['0','1'].includes(params.get('render')) &&
      (!params.has('shot') || /^[0-9]{1,5}$/.test(params.get('shot')||''));
    const versionQuery = (reviewedPreview || reviewedThumbnail) &&
      params.size === 1 && params.has('v') &&
      /^[A-Za-z0-9_.-]{0,80}$/.test(params.get('v')||'');
    const nativeExportQuery = (operation==='api/v1/edit/native-recipe' ||
      operation==='api/v1/edit/native-master' || nativeSource) &&
      (method==='GET' || (nativeSource && method==='HEAD')) &&
      params.has('project_id') && !!params.get('project_id') &&
      params.get('project_id').startsWith('/') &&
      params.get('project_id').length<=1800 &&
      params.size === (operation==='api/v1/edit/native-recipe'?1:2) &&
      (operation==='api/v1/edit/native-recipe' ||
       (params.has('revision') &&
        /^[a-f0-9]{20}$/.test(params.get('revision')||'')));
    if ((operation==='api/v1/edit/native-recipe' ||
         operation==='api/v1/edit/native-master' || nativeSource) &&
        !nativeExportQuery) return {kind:'blocked'};
    const timelineQuery = operation==='api/v1/edit/timeline' &&
      method==='GET' && params.size===1 && params.get('kind')==='music';
    if (operation==='api/v1/edit/timeline' && !timelineQuery)
      return {kind:'blocked'};
    const shotQuery = operation==='api/v1/edit/shot' &&
      method==='GET' && params.size===1 && params.has('index') &&
      /^[0-9]{1,4}$/.test(params.get('index')||'');
    const shotFrame = operation==='api/v1/edit/shot/frame' &&
      method==='GET' && params.size===3 &&
      [...params.keys()].every(k=>['index','choice','revision'].includes(k)) &&
      /^[0-9]{1,4}$/.test(params.get('index')||'') &&
      /^[0-9]{1,2}$/.test(params.get('choice')||'') &&
      /^[a-f0-9]{20}$/.test(params.get('revision')||'');
    if (operation==='api/v1/edit/shot' &&
        !((method==='PATCH' && !address.search) || shotQuery))
      return {kind:'blocked'};
    if (operation==='api/v1/edit/shot/frame' && !shotFrame)
      return {kind:'blocked'};
    const audioQuery = audioRoute && params.size === 1 &&
      params.has('path') && !!params.get('path') &&
      params.get('path').startsWith('/') && params.get('path').length <= 1800;
    if (audioRoute && !audioQuery) return {kind:'blocked'};
    if (address.search && !isStatus && !review && !versionQuery && !audioQuery && !shotQuery && !shotFrame && !nativeExportQuery && !timelineQuery && !sessionRoute)
      return {kind:'blocked'};
    return {kind:'worker', path:nativePrefix + operation + address.search};
  };

  function authHeaders(base, csrf) {
    const h = new Headers(base || {});
    h.set('X-Urano-CSRF', csrf);
    if (generation) h.set('X-Montara-Engine-Generation', String(generation));
    return h;
  }

  // Chema probes Latest at JS startup. Do not wake a cloud worker merely
  // because Google login displayed the Home/Music/Video intro. Resolve the
  // original promise when the genuine Footage/Stage screen is entered.
  let footagePromise = null;
  const whenFootageIsVisible = () => {
    const element = document.getElementById('footage');
    if (!element || !element.hidden) return Promise.resolve();
    if (!footagePromise) {
      footagePromise = new Promise(resolve => {
        const observer = new MutationObserver(() => {
          if (element.hidden) return;
          observer.disconnect();
          resolve();
        });
        observer.observe(element, {attributes:true,attributeFilter:['hidden']});
      });
    }
    return footagePromise;
  };

  // Chema places original thumbnails directly in the review JSON. Native
  // <img>/<video> cannot attach Owner CSRF, so convert ONLY approved media
  // to local blob URLs fetched through the same authenticated gateway.
  const reviewBlobs = new Map();
  const reviewBlob = async nativeUrl => {
    if (!reviewBlobs.has(nativeUrl)) {
      const promise = (async () => {
        const response=await window.fetch(nativeUrl,{cache:'no-store'});
        if (!response.ok) throw new Error('Private Stage preview unavailable');
        const length=Number(response.headers.get('Content-Length')||0);
        if (length > 128*1024*1024)
          throw new Error('Private preview exceeds browser memory limit');
        const blob=await response.blob();
        if (blob.size > 128*1024*1024)
          throw new Error('Private preview exceeds browser memory limit');
        return URL.createObjectURL(blob);
      })();
      reviewBlobs.set(nativeUrl,promise);
      promise.catch(()=>{if(reviewBlobs.get(nativeUrl)===promise)
        reviewBlobs.delete(nativeUrl);});
    }
    return reviewBlobs.get(nativeUrl);
  };
  const decorateReview = async response => {
    if (!response.ok) return response;
    const result=await response.clone().json();
    if (!Array.isArray(result.items) || result.items.length>200)
      return response;
    await Promise.all(result.items.map(async item => {
      if (typeof item.thumbnail === 'string' &&
          /^\/api\/v1\/wizard\/review\/thumbnail\//.test(item.thumbnail)) {
        try {item.thumbnail=await reviewBlob(item.thumbnail);}
        catch {item.thumbnail=null;}
      }
    }));
    const headers=new Headers(response.headers);
    headers.delete('Content-Length');
    headers.delete('Content-Encoding');
    return new Response(JSON.stringify(result),{
      status:response.status,headers
    });
  };

  // The browser may restore older upload path strings after a private worker
  // restart/migration. The authenticated /finish endpoint is idempotent for
  // completed uploads and returns the current Owner-local canonical path.
  // Recover those paths without reuploading bytes or trusting browser file
  // locations. Never use one Owner's files as another Owner's fallback.
  const canonicalUploads=new Map();
  const canonicalAudioForSession=async init => {
    if (typeof init?.body !== 'string' || init.body.length>256000)
      return init;
    let body;
    try {body=JSON.parse(init.body);}catch{return init;}
    if (!body || !Array.isArray(body.tracks) ||
        body.tracks.length<1 || body.tracks.length>32 ||
        !body.tracks.every(t=>typeof t==='string' && t.length<4096))
      return init;
    let changed=false;
    const normalized=[];
    for (const path of body.tracks) {
      const match=/\/Uploads\/([a-f0-9]{32})\/([^/]+)$/.exec(path);
      if (!match || match[2].includes('..')) {
        normalized.push(path); continue;
      }
      const id=match[1];
      let current=canonicalUploads.get(id);
      if (!current) {
        // POST finish is safe and read-only once complete. The original
        // upload endpoint verifies the id against this private worker root.
        const response=await window.fetch('/montara/uploads/'+id+'/finish',{
          method:'POST',headers:{'Content-Type':'application/json'},
          body:'{}'
        });
        if (!response.ok)
          throw new Error('A previously uploaded audio track is not complete. Retry the unfinished track.');
        const result=await response.json();
        const found=[...(result.songs||[]),...(result.master||[])].find(
          x => typeof x.path==='string' && typeof x.name==='string' &&
               x.name===match[2]);
        if (!found || !new RegExp('/Uploads/'+id+'/[^/]+$').test(found.path))
          throw new Error('Cannot verify the audio upload in this private project.');
        current=found.path;
        canonicalUploads.set(id,current);
      }
      normalized.push(current);
      if (current!==path) changed=true;
    }
    const unique=[...new Set(normalized)];
    if (unique.length!==normalized.length)changed=true;
    if (!changed)return init;
    // Track IDs/file metadata remain unchanged. Only canonical private paths
    // and exact duplicate selections are repaired.
    console.info('Montara verified existing audio uploads for this session');
    return {...init,body:JSON.stringify({...body,tracks:unique})};
  };

  window.fetch = async (input, init={}) => {
    const method = String(init.method || input?.method || 'GET').toUpperCase();
    const selected = route(input,method);
    if (!selected) return originalFetch(input, init);
    if (selected.kind === 'blocked')
      throw new Error('Original Montara operation not enabled in this private beta');
    if (selected.kind === 'metadata') {
      if (selected.sampleUnavailable) {
        const hint=document.getElementById('footageHint');
        if (hint) hint.textContent=selected.data.reason;
      }
      return new Response(JSON.stringify(selected.data), {
        status:200, headers:{'Content-Type':'application/json',
                            'Cache-Control':'no-store'}
      });
    }
    // Initial GET from full-session.js is a non-blocking probe. It must not
    // start a VM worker while Home/Video/Music navigation is still visible.
    if (selected.path.startsWith(nativePrefix + 'montara/recovery/latest')) {
      await whenFootageIsVisible();
    }
    const effectiveInit=selected.path===nativePrefix+'montara/session' &&
      method==='POST' ? await canonicalAudioForSession(init) : init;
    const csrf = await token();
    await ensure();
    const headers = authHeaders(effectiveInit.headers || input?.headers, csrf);
    // H4's public edge rejects PATCH. POST to one dedicated owner-authenticated
    // save alias; only the private gateway maps it to Chema's original PATCH.
    const shotSave=method==='PATCH' &&
      selected.path===nativePrefix+'api/v1/edit/shot';
    const response = await originalFetch(
      shotSave ? nativePrefix+'api/v1/edit/shot/save' : selected.path, {
      ...effectiveInit, method:shotSave?'POST':method, headers,
      credentials:'same-origin', cache:'no-store'
    });
    // Original Montara hardcodes a broken /montara/companion/download link.
    // Expose the actual Owner-authenticated pkg only when LAB JM has verified
    // it is published; otherwise hide the dead link, but never fake an
    // installed Engine match to suppress an authentic export warning.
    if (selected.path === nativePrefix+'montara/companion/version' &&
        response.ok) {
      try {
        const release=await response.clone().json();
        const link=document.getElementById('companionUpdateDownload');
        const available=release.installer_available===true &&
          release.download==='/urano/v1/native/companion/download';
        if (link) {
          link.hidden=!available;
          if (available) {
            link.href=release.download;
            link.setAttribute?.('href',release.download);
          } else {
            link.removeAttribute?.('href');
          }
        }
        const hint=document.querySelector?.('#companionUpdateNotice small');
        if (hint) hint.textContent=available
          ? 'Offline Intel macOS Installer for LAB JM. No Terminal or ZIP. macOS approval required. If Companion is busy, installation stops without changes.'
          : 'The matching LAB JM installer is not available yet. Your current Companion still handles uploads; do not reinstall staging236.';
      } catch {
        // Untrusted metadata cannot create a download link.
        document.getElementById('companionUpdateDownload')?.removeAttribute?.('href');
      }
    }
    const next = Number(response.headers.get('X-Montara-Engine-Generation'));
    if (Number.isSafeInteger(next) && next > 0) generation = next;
    if (method==='GET' && selected.path.startsWith(
        nativePrefix + 'api/v1/wizard/review') &&
        selected.path.split('?')[0] === nativePrefix + 'api/v1/wizard/review') {
      return decorateReview(response);
    }
    return response;
  };

  if (typeof HTMLVideoElement !== 'undefined' &&
      typeof HTMLMediaElement !== 'undefined') {
    const descriptor=Object.getOwnPropertyDescriptor(
      HTMLMediaElement.prototype,'src');
    if (descriptor?.get && descriptor?.set) {
      const pending=new WeakMap();
      Object.defineProperty(HTMLVideoElement.prototype,'src',{
        configurable:true,enumerable:descriptor.enumerable,
        get(){return pending.get(this)?.original || descriptor.get.call(this);},
        set(value) {
          const original=String(value);
          const selected=route(original,'GET');
          if (!selected || selected.kind!=='worker' ||
              !selected.path.startsWith(
                nativePrefix+'api/v1/wizard/review/preview/')) {
            pending.delete(this);
            return descriptor.set.call(this,value);
          }
          const task={original};
          pending.set(this,task);
          descriptor.set.call(this,'');
          reviewBlob(original).then(url=>{
            if (pending.get(this)!==task) return;
            descriptor.set.call(this,url);
            this.load();
          }).catch(()=>{
            if(pending.get(this)===task)this.dispatchEvent(new Event('error'));
          });
        }
      });
    }
  }

  // The original cut editor loads individual JPEG frames through new Image().
  // Only the reviewed shot/frame GET is resolved to a private bounded blob;
  // we never expose the Owner CSRF token in a URL or serve the source openly.
  if (typeof HTMLImageElement !== 'undefined') {
    const descriptor=Object.getOwnPropertyDescriptor(
      HTMLImageElement.prototype,'src');
    if (descriptor?.get && descriptor?.set) {
      const pending=new WeakMap();
      Object.defineProperty(HTMLImageElement.prototype,'src',{
        configurable:true,enumerable:descriptor.enumerable,
        get(){return pending.get(this)?.original || descriptor.get.call(this);},
        set(value) {
          const original=String(value);
          const selected=route(original,'GET');
          if (!selected || selected.kind!=='worker' ||
              !selected.path.startsWith(nativePrefix+'api/v1/edit/shot/frame?')) {
            pending.delete(this);
            return descriptor.set.call(this,value);
          }
          const task={original};
          pending.set(this,task);
          descriptor.set.call(this,'');
          reviewBlob(original).then(url=>{
            if (pending.get(this)!==task) return;
            descriptor.set.call(this,url);
          }).catch(()=>{
            if(pending.get(this)===task)this.dispatchEvent(new Event('error'));
          });
        }
      });
    }
  }

  // The original Chema song picker sets HTMLAudioElement.src, which cannot
  // attach the private Owner CSRF header. Resolve reviewed private audio into
  // a bounded browser-local blob; never expose the source path without Owner.
  if (typeof HTMLAudioElement !== 'undefined' &&
      typeof HTMLMediaElement !== 'undefined') {
    const descriptor=Object.getOwnPropertyDescriptor(
      HTMLMediaElement.prototype,'src');
    if (descriptor?.get && descriptor?.set) {
      const pending=new WeakMap();
      Object.defineProperty(HTMLAudioElement.prototype,'src',{
        configurable:true,enumerable:descriptor.enumerable,
        get(){return pending.get(this)?.original || descriptor.get.call(this);},
        set(value) {
          const original=String(value);
          const selected=route(original,'GET');
          if (!selected || selected.kind!=='worker' ||
              !selected.path.startsWith(nativePrefix+'montara/audio?') &&
              !/^\/urano\/v1\/native\/rpc\/montara\/session\/[a-f0-9]{12}\/listen(?:\?|$)/.test(selected.path)) {
            pending.delete(this);
            return descriptor.set.call(this,value);
          }
          const task={original};
          pending.set(this,task);
          descriptor.set.call(this,'');
          reviewBlob(original).then(url=>{
            if (pending.get(this)!==task) return;
            descriptor.set.call(this,url);
            this.load();
          }).catch(()=>{
            if (pending.get(this)===task)this.dispatchEvent(new Event('error'));
          });
        }
      });
    }
  }

  // new Audio(url) initializes src inside the native constructor, which may
  // bypass the JS prototype setter above. Route that constructor form through
  // the exact same CSRF-protected src assignment; all other Audio usage stays
  // native. Returning an HTMLAudioElement preserves play/pause/seek behavior.
  if (typeof window.Audio === 'function' &&
      typeof HTMLAudioElement !== 'undefined') {
    const NativeAudio = window.Audio;
    function PrivateOwnerAudio(src) {
      const audio = new NativeAudio();
      if (src !== undefined && src !== null) audio.src = String(src);
      return audio;
    }
    PrivateOwnerAudio.prototype = NativeAudio.prototype;
    Object.setPrototypeOf(PrivateOwnerAudio, NativeAudio);
    window.Audio = PrivateOwnerAudio;
  }

  // Full-session audio/result links have no way to attach CSRF. Resolve each
  // download through the same verified Owner bridge, bounded like previews.
  if (typeof document.addEventListener === 'function') {
    document.addEventListener('click', event => {
      const anchor = event.target?.closest?.('a[href]');
      if (!anchor) return;
      const original = anchor.getAttribute('href') || '';
      if (!/^\/montara\/session\/[a-f0-9]{12}\/(?:results\.zip|result\/[1-9][0-9]{0,3}(?:\?download=1)?)$/.test(original))
        return;
      const selected = route(original, 'GET');
      if (!selected || selected.kind !== 'worker') return;
      event.preventDefault();
      (async () => {
        const response = await window.fetch(original);
        if (!response.ok) throw new Error('Private session download unavailable');
        const max = 128 * 1024 * 1024;
        if (Number(response.headers.get('Content-Length') || 0) > max)
          throw new Error('Session download exceeds private media limit');
        const blob = await response.blob();
        if (blob.size > max) throw new Error('Session download exceeds private media limit');
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = original.includes('results.zip') ? 'Montara-session.zip' : 'Montara-song.mp3';
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 60000);
      })().catch(err => console.error('Montara session download:', err.message));
    });
  }

  // Chema also uses XHR for imported media. Keep the original XHR event
  // semantics; no replacement uploader or form is created here.
  if (typeof XMLHttpRequest !== 'undefined') {
    const open = XMLHttpRequest.prototype.open;
    const send = XMLHttpRequest.prototype.send;
    const abort = XMLHttpRequest.prototype.abort;
    const selection = new WeakMap();
    XMLHttpRequest.prototype.open = function(method, url, ...other) {
      const nativeMethod = String(method).toUpperCase();
      const target = route(url,nativeMethod);
      const asynchronous = other[0] !== false;
      if (target && (!asynchronous || target.kind === 'blocked' ||
                     target.kind === 'metadata')) {
        throw new Error('Original Montara operation not enabled in this private beta');
      }
      selection.set(this, {target, method:nativeMethod, cancelled:false});
      return open.call(this, nativeMethod,
                       target?.kind === 'worker' ? target.path : url, ...other);
    };
    XMLHttpRequest.prototype.send = function(body) {
      const current = selection.get(this);
      if (!current?.target) return send.call(this,body);
      Promise.all([token(),ensure()]).then(([csrf]) => {
        if (current.cancelled) return;
        this.setRequestHeader('X-Urano-CSRF', csrf);
        if (generation)
          this.setRequestHeader('X-Montara-Engine-Generation',String(generation));
        send.call(this,body);
      }).catch(() => {
        if (!current.cancelled) abort.call(this);
      });
    };
    XMLHttpRequest.prototype.abort = function() {
      const current = selection.get(this);
      if (current) current.cancelled = true;
      return abort.call(this);
    };
  }
})();
