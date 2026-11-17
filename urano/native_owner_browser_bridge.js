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
    'api/v1/wizard/song-open', 'api/v1/wizard/draft', 'api/v1/wizard/prepare', 'api/v1/wizard/start',
    'api/v1/wizard/cancel', 'api/v1/wizard/status',
    'api/v1/project', 'montara/recovery/latest',
    'api/v1/artifacts/sync',
    'api/v1/wizard/review', 'api/v1/wizard/review/replace',
    'api/v1/wizard/review/render',
    'api/v1/wizard/upload','montara/uploads','montara/branding',
    'api/v1/edit/shot', 'api/v1/edit/shot/frame',
    'api/v1/edit/native-recipe','api/v1/edit/native-master',
    'api/v1/edit/timeline',
    'api/v1/settings/song-camera-move', 'api/v1/settings/fillers','api/v1/settings/video-light',
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

  const translations = window.MontaraWorkI18n;
  translations.captureStatic(document.body);


  document.addEventListener('DOMContentLoaded', async () => {
    const labels = [];
    const response = await originalFetch('/urano/v1/session/account');
    if (!response.ok) return;
    const account = await response.json();
    const accountControl = document.createElement('div');
    accountControl.className = 'montara-work-account';
    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'montara-work-avatar';
    trigger.setAttribute('aria-label', 'Google account');
    trigger.setAttribute('popovertarget', 'montaraWorkAccountPanel');
    const initials = (account.name || account.email || 'Google User').trim()
      .split(/\s+/).slice(0, 2).map(word => Array.from(word)[0]).join('').toUpperCase();
    trigger.textContent = initials;
    if (account.picture) {
      const avatar = document.createElement('img');
      avatar.referrerPolicy = 'no-referrer';
      avatar.alt = '';
      avatar.addEventListener('load', () => trigger.replaceChildren(avatar), {once:true});
      avatar.src = account.picture;
    }
    let locale = account.language || 'en';
    const translate = text => translations.translate(text);
    const refreshLabels = () => {
      translations.setLocale(locale);
      for (const [node, original] of labels) {
        node.textContent = original.replace(original.trim(), translate(original.trim()));
      }
      search.placeholder = translate('Search projects');
      search.setAttribute('aria-label', search.placeholder);
      dialog.setAttribute('aria-label', translate('Your Projects'));
      render();
    };
    const menu = document.createElement('div');
    menu.id = 'montaraWorkAccountPanel';
    menu.className = 'montara-work-account-panel';
    menu.setAttribute('popover', 'auto');
    const identity = document.createElement('strong');
    identity.textContent = account.name || 'Google account';
    const email = document.createElement('p');
    email.textContent = account.email || 'Vuelve a iniciar sesión para mostrar tu perfil.';
    const status = document.createElement('div');
    status.setAttribute('role', 'status');
    const button = (label, action) => {
      const control = document.createElement('button');
      control.type = 'button';
      control.textContent = label;
      labels.push([control.firstChild, label]);
      control.addEventListener('click', async () => {
        control.disabled = true;
        try { await action(); }
        catch { status.textContent = 'No se pudo completar la acción. Recarga e inténtalo de nuevo.'; }
        finally { control.disabled = false; }
      });
      return control;
    };
    const logout = async next => {
      const result = await originalFetch('/urano/v1/session/logout', {
        method: 'POST', headers: {'X-Urano-CSRF': await token()}
      });
      if (!result.ok && result.status !== 401) throw new Error('Logout failed');
      location.replace(next);
    };
    // Dialog structure, project search and list presentation from FER PR #189.
    const dialog = document.createElement('dialog');
    dialog.className = 'montara-owner-dialog';
    dialog.setAttribute('aria-label', 'Your Projects');
    const top = document.createElement('div');
    top.className = 'montara-owner-top';
    const title = document.createElement('h2');
    title.textContent = 'Your Projects';
    labels.push([title.firstChild, 'Your Projects']);
    top.append(title, button('Close', () => dialog.close()));
    const search = document.createElement('input');
    search.type = 'search';
    search.placeholder = 'Search projects';
    search.setAttribute('aria-label', 'Search projects');
    const list = document.createElement('ul');
    list.className = 'montara-owner-list';
    const hint = document.createElement('p');
    hint.setAttribute('role', 'status');
    dialog.append(top, search, list, hint);
    dialog.addEventListener('close', () => trigger.focus());
    let rows = [];
    const render = () => {
      const query = search.value.trim().toLowerCase();
      list.replaceChildren();
      for (const project of rows) {
        const name = project.title || project.name || 'Untitled project';
        if (!name.toLowerCase().includes(query)) continue;
        const item = document.createElement('li');
        item.textContent = name;
        list.append(item);
      }
      hint.textContent = list.childElementCount ? '' : translate('No projects found.');
    };
    search.addEventListener('input', render);
    const projects = button('Your Projects', async () => {
      const result = await window.fetch('/api/v1/wizard/projects', {cache:'no-store'});
      if (!result.ok) throw new Error('Projects unavailable');
      rows = (await result.json()).projects;
      search.value = '';
      render();
      menu.hidePopover();
      dialog.showModal();
      search.focus();
    });
    const settings = button('Settings', () => {
      const options = document.getElementById('stageAudioOptions');
      menu.hidePopover();
      options.open = true;
      options.querySelector('summary').focus();
      options.scrollIntoView({block:'nearest'});
    });
    menu.addEventListener('beforetoggle', () => {
      const options = document.getElementById('stageAudioOptions');
      settings.hidden = !options?.getClientRects().length;
    });
    const language = document.createElement('label');
    language.append('Language ');
    labels.push([language.firstChild, 'Language ']);
    const select = document.createElement('select');
    for (const [code, name] of Object.entries({en:'English', es:'Español', de:'Deutsch', fr:'Français'})) {
      select.append(new Option(name, code));
    }
    select.value = locale;
    select.addEventListener('change', async () => {
      select.disabled = true;
      try {
        const response = await originalFetch('/urano/v1/session/language', {
          method:'POST',
          headers:{'Content-Type':'application/json', 'X-Urano-CSRF':await token()},
          body:JSON.stringify({language:select.value})
        });
        if (!response.ok) throw new Error('Language unavailable');
        locale = (await response.json()).language;
        refreshLabels();
      } catch {
        select.value = locale;
        status.textContent = 'Could not save language.';
      } finally { select.disabled = false; }
    });
    language.append(select);
    menu.append(identity, email, language, projects, settings,
      button('Switch Account', () => logout('/urano/v1/google/start')),
      button('Log Out', () => logout('/urano/v1/session/signed-out')), status);
    accountControl.append(trigger, menu);
    document.body.append(accountControl, dialog);
    refreshLabels();
  });

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
    if (p === '/montara/branding' && method === 'GET')
      return { kind:'metadata', data:{mode:'montara',has_logo:false} };
    if (p === '/montara/logo' && method === 'POST')
      return {kind:'unsupported', message:'Custom logo upload is unavailable in staging. Choose Montara Watermark or No branding.'};
    const operation = p.substring(1);
    const session = (method === 'POST' && (operation === 'montara/session' ||
      /^montara\/session\/[a-f0-9]{12}\/(songs|prepare|render|cancel|include|video-master)$/.test(operation))) ||
      (method === 'GET' && /^montara\/session\/(latest|[a-f0-9]{12}(?:\/(?:waveform|video-source))?)$/.test(operation));
    const sessionListen = (method === 'GET' || method === 'HEAD') &&
      /^montara\/session\/[a-f0-9]{12}\/listen$/.test(operation);
    const songResult = method === 'GET' && /^api\/v1\/wizard\/song-result\/[a-f0-9]{32}$/.test(operation);
    const resumable = /^montara\/uploads\/[a-f0-9]{32}(?:\/finish)?$/.test(operation);
    const audioRoute = operation === 'montara/audio' && method === 'GET';
    const nativeSource = /^api\/v1\/edit\/native-source\/[0-9]{1,3}$/.test(
      operation) && (method==='HEAD' || method==='GET');
    const reviewedPreview = /^api\/v1\/wizard\/review\/preview\/[0-9]{1,5}$/.test(operation);
    const reviewedThumbnail = /^api\/v1\/wizard\/review\/thumbnail\/(?:assets-v2|[a-f0-9]{16,128})\/[A-Za-z0-9_.-]{1,180}$/.test(operation);
    if (address.hash || (!routes.has(operation) && !audioRoute && !resumable && !session && !sessionListen && !songResult &&
                         !reviewedPreview && !reviewedThumbnail && !nativeSource))
      return {kind:'blocked'};
    const params = address.searchParams;
    const songMoveQuery = operation === 'api/v1/settings/song-camera-move' && method === 'GET' &&
      params.size === 2 && /^[a-f0-9]{32}$/.test(params.get('song_id') || '') &&
      (params.get('source') || '').startsWith('/');
    const songResultQuery = songResult && params.size === 1 &&
      (params.get('project_id') || '').startsWith('/') && params.get('project_id').length <= 1800;
    if (songResult && !songResultQuery) return {kind:'blocked'};
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
    if (address.search && !isStatus && !review && !versionQuery && !audioQuery && !shotQuery && !shotFrame && !nativeExportQuery && !timelineQuery && !songResultQuery && !songMoveQuery)
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

  window.fetch = async (input, init={}) => {
    const method = String(init.method || input?.method || 'GET').toUpperCase();
    const selected = route(input,method);
    if (!selected) return originalFetch(input, init);
    if (selected.kind === 'blocked')
      throw new Error('Original Montara operation not enabled in this private beta');
    if (selected.kind === 'unsupported')
      return new Response(JSON.stringify({error:{message:selected.message}}), {
        status:501, headers:{'Content-Type':'application/json','Cache-Control':'no-store'}
      });
    if (selected.kind === 'metadata')
      return new Response(JSON.stringify(selected.data), {
        status:200, headers:{'Content-Type':'application/json',
                            'Cache-Control':'no-store'}
      });
    // Initial GET from full-session.js is a non-blocking probe. It must not
    // start a VM worker while Home/Video/Music navigation is still visible.
    if (selected.path.startsWith(nativePrefix + 'montara/recovery/latest')) {
      await whenFootageIsVisible();
    }
    const csrf = await token();
    await ensure();
    const headers = authHeaders(init.headers || input?.headers, csrf);
    // H4's public edge rejects PATCH. POST to one dedicated owner-authenticated
    // save alias; only the private gateway maps it to Chema's original PATCH.
    const shotSave=method==='PATCH' &&
      selected.path===nativePrefix+'api/v1/edit/shot';
    const response = await originalFetch(
      shotSave ? nativePrefix+'api/v1/edit/shot/save' : selected.path, {
      ...init, method:shotSave?'POST':method, headers,
      credentials:'same-origin', cache:'no-store'
    });
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
              !(selected.path.startsWith(nativePrefix+'montara/audio?') ||
                /^montara\/session\/[a-f0-9]{12}\/listen$/.test(selected.path.slice(nativePrefix.length)))) {
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
