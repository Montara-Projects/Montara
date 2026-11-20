/* Optional Stage session flow; the single-song journey stays unchanged. */
const fullSession = { id: null, active: false, data: null, busy: false };
if(typeof api==='function')api('/montara/recovery/latest').then(()=>{$('#sessionResume').hidden=false;}).catch(()=>{});
$('#sessionResume').onclick = async () => {
  try {
    const recent=await api('/montara/recovery/latest');
    if(recent.kind==='project'){
      const current=await status();
      if(['running','cancelling'].includes(current.status))return toast('A video is still being made.');
      if(current.project_path!==recent.path)await api('/wizard/projects/open',{path:recent.path});
      location.assign('/?resume=footage');return;
    }
    const latest=recent;
    fullSession.id=latest.id;
    try {localStorage.setItem('montara-session',latest.id);} catch {}
    fullSession.localProgress = {}; fullSession.localResults = [];
    fullSession.active = true;
    fullSession.forVideo = false;
    show('sessionReview'); $('#sessionSongs').hidden = false; clearSessionResults();
    const data = await waitSession(await api(`/montara/session/${fullSession.id}`));
    fullSession.mixes=data.saved_song_mixes || fullSession.mixes || {};
    fullSession.mixCache ||= {};
    if (data.songs) drawSessionSongs(data.songs);
    if (data.results?.length) drawSessionResults(data);
  } catch (error) {
    if(error.session?.saved_song_mixes)fullSession.mixes=error.session.saved_song_mixes;
    if (error.session?.songs) drawSessionSongs(error.session.songs);
    if (error.session?.results?.length) drawSessionResults(error.session);
    toast(error.message, true);
  }
};
$('#stageAudioOnly').addEventListener('change', renderFiles);
$('#fullSessionOn').addEventListener('change', renderFiles);
$('#sessionBack').onclick = () => {
  if (fullSession.busy || fullSession.cancelling) return toast('Cancel the session job first.');
  fullSession.active = false;
  show('footage');
};
$('#sessionCancel').onclick = async () => {
  if(fullSession.cancelling)return;
  fullSession.cancelling=true;
  fullSession.cancelRequested = true;
  fullSession.mixAbort?.abort();
  if (fullSession.videoMatching) {
    work.cancelled = true; work.generation++;
    await api('/wizard/cancel', {});
  }
  $('#sessionCancel').disabled=true;$('#sessionStatus').textContent='Cancelling…';
  try {
    if(fullSession.mixPromise)try{await fullSession.mixPromise;}catch(error){if(error.name!=='AbortError')throw error;}
    await Promise.allSettled([...sessionPending]);
    await api(`/montara/session/${fullSession.id}/cancel`, {});
    let data=await api(`/montara/session/${fullSession.id}`);
    while(['detecting','preparing','rendering'].includes(data.status)){
      await new Promise(resolve=>setTimeout(resolve,250));
      data=await api(`/montara/session/${fullSession.id}`);
    }
    showSessionProgress({...data,status:'cancelled'});
  }
  catch (error) { fullSession.busy=true;$('#sessionBack').disabled=true;$('#sessionCancel').hidden=false;toast('Could not confirm cancellation. '+error.message, true); }
  finally{fullSession.cancelling=false;$('#sessionCancel').disabled=false;}
};
const sessionPending=new Set();
function checkSessionCancel(){if(fullSession.cancelRequested)throw new DOMException('Session cancelled','AbortError');}
async function sessionRequest(path,body){
  checkSessionCancel();const request=api(path,body);sessionPending.add(request);
  try{const data=await request;checkSessionCancel();return data;}finally{sessionPending.delete(request);}
}

const SESSION_STAGE = {
  detecting: ['Finding the songs in your session', 'Listening to every track to find where each song starts and ends.'],
  preparing: ['Preparing the mixer preview', 'Cutting a short excerpt of the first selected song for the mixer.'],
  rendering: ['Mixing songs', ''],
};
const sessionClock = { status: null, started: 0 };

const minutesLeft = seconds => seconds < 50 ? 'less than a minute left' : `about ${Math.round(seconds / 60)} min left`;

function showSessionProgress(data) {
  fullSession.data = data;
  fullSession.busy = ['detecting', 'preparing', 'rendering'].includes(data.status);
  const now = performance.now() / 1000;
  if (sessionClock.status !== data.status) Object.assign(sessionClock, { status: data.status, started: now });
  const [title, hint] = fullSession.forVideo && ['detecting','rendering'].includes(data.status)
    ? [data.status==='detecting' ? 'Analysing your tracks' : 'Mixing and mastering your song', ''] : SESSION_STAGE[data.status] || [];
  $('#sessionHint').hidden = fullSession.forVideo || ['rendering','done','partial'].includes(data.status);
  $('#sessionHint').textContent = hint || 'Review the suggested boundaries and choose the songs. Each song gets its own automatic mix; your fader moves apply on top.';
  $('#sessionCancel').hidden = !fullSession.busy;
  $('#sessionBack').disabled = fullSession.busy;
  $('#sessionWorking').hidden = !fullSession.busy && !data.error;
  $('#sessionWorking').classList.toggle('done', !fullSession.busy);
  $('#sessionProgress').hidden = !fullSession.busy;
  const percent = Math.max(0, Math.min(100, Number(data.progress?.progress || 0)));
  $('#sessionProgress').value = percent;
  const detail = data.progress?.stage_detail || '';
  $('#sessionStatus').textContent = data.error || (fullSession.busy ? `${title}${detail && detail !== data.status ? ' · ' + detail : ''}…` : '');
  // Detection estimate; song progress comes from the workers below.
  let eta = '';
  if (fullSession.busy && data.status !== 'rendering' && percent > 2) {
    const elapsed = now - sessionClock.started;
    eta = minutesLeft(elapsed * (100 - percent) / percent);
  }
  $('#sessionEta').textContent = fullSession.busy ? eta : '';
  paintSessionRender(data);
  if (data.results?.length) drawSessionResults(data);
}

async function waitSession(initial) {
  let data = initial;
  while (['detecting', 'preparing', 'rendering'].includes(data.status)) {
    showSessionProgress(data);
    await new Promise(resolve => setTimeout(resolve, 800));
    data = await api(`/montara/session/${fullSession.id}`);
  }
  showSessionProgress(data);
  if (data.status === 'failed' || data.status === 'cancelled') {
    const error = new Error(data.error || 'Session stopped.'); error.session = data; throw error;
  }
  return data;
}

async function openFullSession(forVideo = false) {
  if(fullSession.cancelling)return;
  fullSession.forVideo = forVideo === true;
  fullSession.cancelRequested=false;
  if (!audioTracks().length) return toast('Add the audio tracks of your session first.', true);
  fullSession.active = true;
  show('sessionReview');
  $('#sessionSongs').hidden = false;
  $('#sessionSongs').replaceChildren(); clearSessionResults();
  $('#sessionMix').hidden = true;
  try {
    const tracks = audioTracks().map(f => f.path);
    const job = await api('/montara/session', { tracks, track_types: TrackTypes.forFiles(tracks), for_video:forVideo });
    fullSession.id = job.id; fullSession.mixes = {}; fullSession.mixCache = {}; fullSession.mixSong = null;
    fullSession.localProgress = {}; fullSession.localResults = [];
    try { localStorage.setItem('montara-session', job.id); $('#sessionResume').hidden = false; } catch { /* optional */ }
    const data = await waitSession(job);
    if (forVideo) return await mixSessionForVideo(data);
    drawSessionSongs(data.songs);
    $('#sessionStatus').textContent = data.ai_review?.status === 'reviewed' ? `AI reviewed ${data.ai_review.submitted_cuts} of ${data.ai_review.total_cuts} cuts · ${data.ai_review.value.summary}` : 'Acoustic suggestions — check each song before continuing.';
  } catch (error) {
    if (forVideo && fullSession.data?.video_excerpt) fullSession.data.songs?.forEach(song => {song.selected=false;});
    if (forVideo && fullSession.data?.songs) drawSessionSongs(fullSession.data.songs);
    if (!fullSession.cancelRequested) {
      showSessionProgress({...fullSession.data,status:'failed',error:error.message});
      toast(error.message, true);
    }
  }
}

async function mixSessionForVideo(data) {
  // Reuse the engine's real onset/spectral sync, not a second matching algorithm.
  const generation = beginWork();
  fullSession.busy = true;
  fullSession.videoMatching = true;
  $('#sessionWorking').classList.remove('done');
  $('#sessionProgress').hidden=true;
  $('#sessionEta').textContent='';
  $('#sessionBack').disabled=true;
  $('#sessionStatus').textContent = 'Finding your song from the camera audio…';
  $('#sessionWorking').hidden = false;
  $('#sessionCancel').hidden = false;
  try {
    const guide = await api(`/montara/session/${fullSession.id}/video-source`);
    let input = {master:guide.master, songs:'', videos:inputs().videos};
    await api('/wizard/projects/new', {});
    const draft = await api('/wizard/draft', {name:$('#videoName').value.trim() || todayName(), platform:'youtube', ...input, audio_paths:[guide.master]});
    state.projectId = draft.project_id;
    const prepared = await prepareStageSources(generation,input,$('#videoName').value.trim() || todayName());
    input=prepared.input;
    const sync=prepared.sync;
    fullSession.videoMatching = false;
    checkSessionCancel();
    const song = data.video_excerpt ? SessionVideo.excerptForClips(data.duration, sync.clips)
      : SessionVideo.songForClips(data.songs, sync.clips);
    fullSession.data.songs = data.video_excerpt ? [song]
      : data.songs.map(s=>({...s, selected:s.id===song.id, confirmed:s.id===song.id}));
    drawSessionSongs();
    // Camera + stems: one automatic mix/master, without preparing a separate
    // browser mixer preview. Audio-only Full session still opens its song review.
    await renderFullSession(true);
  } finally { fullSession.busy = false; fullSession.videoMatching = false; }
}

// ---------- song list: waveform, handles, listen, per-song mixer ----------
// Songs live in fullSession.data.songs; the page edits that list directly.
const sessionWave = { id: null, data: null, loading: null };
const sessionPlayer = { audio: null, index: -1, raf: 0 };
fullSession.mixes = fullSession.mixes || {};   // song id -> changes made in that song's mixer

// clock() comes from montara.js (m:ss).
const songList = () => fullSession.data.songs;

async function loadSessionWave() {
  if (sessionWave.id === fullSession.id && (sessionWave.data || sessionWave.loading)) return sessionWave.loading || sessionWave.data;
  sessionWave.id = fullSession.id; sessionWave.data = null;
  // Drawn in the background after detection: ask again until it is there.
  const id = fullSession.id;
  sessionWave.loading = (async () => {
    for (let attempt = 0; attempt < 200 && fullSession.id === id; attempt++) {
      const data = await api(`/montara/session/${id}/waveform`).catch(() => null);
      if (data?.peaks) return (sessionWave.data = data);
      if (!data?.pending) return null;
      await new Promise(resolve => setTimeout(resolve, 3000));
    }
    return null;
  })().finally(() => { sessionWave.loading = null; });
  return sessionWave.loading;
}

// What each row shows: the song plus a margin, so a handle can be dragged outwards.
function songView(i) {
  const songs = songList(), song = songs[i], length = song.end - song.start;
  const pad = Math.min(90, Math.max(12, length * .15));
  return { from: Math.max(0, song.start - pad), to: Math.min(fullSession.data.duration, song.end + pad) };
}

// Long segments can be jams, medleys, or multiple songs joined by detection.
// Never split without listening: request an explicit human review before export.
const LONG_SONG_REVIEW_SECONDS = 8 * 60;
function longSongsNeedingReview(songs) {
  return songs.filter(song => song.selected && song.end - song.start >= LONG_SONG_REVIEW_SECONDS);
}
function parseConcertSplitTime(text) {
  const value = String(text || '').trim();
  if (!/^[0-9]+(?::[0-5][0-9]){0,2}$/.test(value)) return NaN;
  return value.split(':').map(Number).reduce((seconds, part) => seconds * 60 + part, 0);
}
function confirmLongSongReview(songs) {
  const long = longSongsNeedingReview(songs);
  if (!long.length) return true;
  const descriptions = long.map(song => '- ' + song.name + ': ' +
    clock(song.start) + '-' + clock(song.end) + ' (' + clock(song.end-song.start) + ')').join('\n');
  return window.confirm(
    'Review long song boundaries before exporting:\n\n' + descriptions +
    '\n\nMontara may have merged several songs. Use Play and Split at the concert timestamp, or confirm these are genuinely long songs or medleys. Continue?'
  );
}

function drawSessionSongs(songs) {
  if (songs) fullSession.data.songs = songs;
  stopSongPreview();
  const list = songList();
  let selection=document.querySelector('#sessionBulkSelection');
  if (!selection) {
    selection=document.createElement('div'); selection.id='sessionBulkSelection';
    selection.className='actions';
    selection.innerHTML='<button class="btn ghost small" type="button" data-select-all>Select all</button>'+
      '<button class="btn ghost small" type="button" data-select-none>Clear selection</button>'+
      '<span data-count></span>';
    $('#sessionSongs').before(selection);
    selection.addEventListener('click',event=>{
      const all=event.target.closest('[data-select-all]'),none=event.target.closest('[data-select-none]');
      if (!all&&!none)return;
      const songs=songList().map(song=>({...song,selected:!!all}));
      if(all&&songs.length>30)return toast('Maximum 30 songs.',true);
      drawSessionSongs(songs);
    });
  }
  selection.querySelector('[data-count]').textContent=
    list.filter(song=>song.selected).length+' / '+list.length+' selected · max 30';
  $('#sessionSongs').innerHTML = list.map((song, i) => `<div class="session-song" data-session-song="${i}">
    <div class="song-head">
      <input data-song-field="selected" type="checkbox" ${song.selected ? 'checked' : ''} aria-label="Export song ${i + 1}">
      <button class="song-play" type="button" data-song-play="${i}" aria-label="Listen to song ${i + 1}">▶</button>
      ${(fullSession.data.results || []).some(r=>r.id===song.id &&
        Math.abs(r.start-song.start)<.01 && Math.abs(r.end-song.end)<.01) ?
        `<button class="btn ghost small" type="button" data-song-master="${i}" title="Listen to the entire mastered song (not the raw boundary guide)">Play final mix</button>` : ''}
      <span class="song-num">${String(i + 1).padStart(2, '0')}</span>
      <input aria-label="Song name" data-song-field="name" value="${escapeHtml(song.name)}" maxlength="80">
      ${fullSession.mixes[song.id] ? '<span class="song-tag">Own mix</span>' : ''}
      ${fullSession.data.uses_previews ? `<span class="song-tag confirm-state" data-confirm-state="${i}"></span>
      <button class="btn ghost small" data-song-confirm="${i}" type="button" ${song.confirmed ? 'hidden' : ''} title="These cuts are final: start sending this song's original audio now">Confirm</button>` : ''}
      <button class="btn ghost small" data-song-mixer="${i}" type="button">Mixer</button>
      ${song.end - song.start >= LONG_SONG_REVIEW_SECONDS ? '<span class="song-tag" title="Check this cut: listen and split by concert timestamp before export">Review long cut</span>' : ''}
      <button class="btn ghost small" data-song-split="${i}" type="button">Split</button>
      <button class="btn ghost small" data-song-remove="${i}" type="button" ${list.length === 1 ? 'disabled' : ''}>Remove</button>
    </div>
    <div class="song-wave" data-song-wave="${i}">
      <canvas aria-hidden="true"></canvas>
      <i class="song-cut start" data-handle="start" role="slider" tabindex="0" aria-label="Start of song ${i + 1}" aria-valuetext="${clock(song.start)}"></i>
      <i class="song-cut end" data-handle="end" role="slider" tabindex="0" aria-label="End of song ${i + 1}" aria-valuetext="${clock(song.end)}"></i>
      <i class="song-playhead" hidden></i>
      <span class="song-time">${clock(song.start)} – ${clock(song.end)} · ${clock(song.end - song.start)}</span>
    </div>
    ${song.review_note ? `<p class="hint">${song.needs_review ? 'Review · ' : ''}${escapeHtml(song.review_note)}</p>` : ''}
  </div>`).join('');
  // Reprocess the cached instrument envelopes without re-upload or a
  // destructive change. The user reviews the returned suggestions first.
  let reanalyze = document.querySelector('#sessionFindSongSplits');
  if (!reanalyze) {
    reanalyze = document.createElement('button');
    reanalyze.id = 'sessionFindSongSplits';
    reanalyze.type = 'button';
    reanalyze.className = 'btn ghost small';
    reanalyze.textContent = 'Improve song boundaries';
    reanalyze.title = 'Find transitions inside long songs from recorded instruments; review before saving';
    $('#sessionSongs').before(reanalyze);
    reanalyze.addEventListener('click', async () => {
      if (!fullSession.id || fullSession.busy) return;
      if (!window.confirm('Montara will search for instrument changes inside long songs. These are suggestions, not confirmed song endings. Listen and review the splits. Continue?')) return;
      const previous = songList().map(song => ({...song}));
      reanalyze.disabled = true;
      try {
        const draft = await sessionRequest('/montara/session/' + fullSession.id + '/suggest', {songs: previous});
        if (!draft.transitions?.length) return toast('No new instrument transition suggestions were found.');
        // Only unchanged intervals inherit saved mixes. Each newly split
        // section needs its own Mixer; old source files remain untouched.
        const known = new Map(previous.map(song => [song.start + '-' + song.end, song]));
        const preserved = {};
        const revised = draft.songs.map((song, index) => {
          const original = known.get(song.start + '-' + song.end);
          if (original && fullSession.mixes[original.id]) preserved[index + 1] = fullSession.mixes[original.id];
          return {...song, confirmed: original?.confirmed || false};
        });
        fullSession.mixes = preserved;
        fullSession.mixCache = {};
        drawSessionSongs(revised);
        toast(draft.transitions.length + ' possible transitions added. Listen and confirm the cuts before exporting.');
      } catch (error) {
        toast(error.message || 'Could not improve the song boundaries.', true);
      } finally {
        reanalyze.disabled = false;
      }
    });
  }
  reanalyze.hidden = !list.some(song => song.end - song.start > 600);
  list.forEach((_, i) => paintSong(i));
  const empty = fullSession.data.empty_tracks || [];
  $('#sessionEmpty').hidden = !empty.length;
  $('#sessionEmpty').innerHTML = empty.length ? `Left out, no sound in the whole session (not sent, not mixed): ${empty.map(f => `${escapeHtml(f.replace(/\.wav$/i, ''))} <button class="link" type="button" data-include-track="${escapeHtml(f)}">use it anyway</button>`).join(' · ')}` : '';
  paintUploadState();
  loadSessionWave().then(() => list.forEach((_, i) => paintSong(i)));
  warmSessionAudio();
  $('#sessionMix').hidden = false;
  $('#sessionMix').textContent = fullSession.forVideo ? 'Review this song’s mix' : 'Export selected songs';
}

function paintSong(i) {
  const row = document.querySelector(`[data-song-wave="${i}"]`);
  if (!row) return;
  const song = songList()[i], view = songView(i), canvas = row.querySelector('canvas');
  const width = row.clientWidth || 600, height = row.clientHeight || 64, ratio = devicePixelRatio || 1;
  canvas.width = width * ratio; canvas.height = height * ratio;
  const g = canvas.getContext('2d'); g.scale(ratio, ratio); g.clearRect(0, 0, width, height);
  const x = t => (t - view.from) / Math.max(.001, view.to - view.from) * width;
  const wave = sessionWave.data, styles = getComputedStyle(document.documentElement);
  const accent = styles.getPropertyValue('--accent').trim() || '#FF4F2E', muted = styles.getPropertyValue('--muted').trim() || '#8a8a8f';
  if (wave) {
    for (let px = 0; px < width; px++) {
      const t0 = view.from + px / width * (view.to - view.from), t1 = view.from + (px + 1) / width * (view.to - view.from);
      let peak = 0;
      for (let c = Math.floor(t0 / wave.step); c <= Math.floor(t1 / wave.step); c++) peak = Math.max(peak, wave.peaks[c] || 0);
      const h = Math.max(1, peak / 255 * (height - 8));
      const inside = t1 > song.start && t0 < song.end;
      g.fillStyle = inside ? accent : muted; g.globalAlpha = inside ? .9 : .35;
      g.fillRect(px, (height - h) / 2, 1, h);
    }
    g.globalAlpha = 1;
  } else {
    g.fillStyle = muted; g.globalAlpha = .25; g.fillRect(0, height / 2 - 1, width, 2); g.globalAlpha = 1;
    g.font = '12px Inter, system-ui, sans-serif'; g.fillStyle = muted; g.fillText('Drawing the waveform…', 10, 16);
  }
  row.querySelector('.start').style.left = `${x(song.start)}px`;
  row.querySelector('.end').style.left = `${x(song.end)}px`;
  row.querySelector('.song-time').textContent = `${clock(song.start)} – ${clock(song.end)} · ${clock(song.end - song.start)}`;
}

// Drag a handle: the start can not pass the previous song's end, nor the end the next song's start.
$('#sessionSongs').addEventListener('pointerdown', event => {
  const handle = event.target.closest('[data-handle]');
  if (!handle) return;
  const row = handle.closest('[data-song-wave]'), i = Number(row.dataset.songWave), view = songView(i);
  const songs = songList(), song = songs[i], rect = row.getBoundingClientRect();
  handle.setPointerCapture(event.pointerId);
  const move = e => {
    const t = view.from + Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width)) * (view.to - view.from);
    if (handle.dataset.handle === 'start') song.start = Math.max(i ? songs[i - 1].end : 0, Math.min(t, song.end - 1));
    else song.end = Math.min(i < songs.length - 1 ? songs[i + 1].start : fullSession.data.duration, Math.max(t, song.start + 1));
    song.start = Math.round(song.start * 10) / 10; song.end = Math.round(song.end * 10) / 10;
    if (song.confirmed) { song.confirmed = false; paintConfirm(i); }  // new cuts: confirm again
    handle.setAttribute('aria-valuetext', clock(song[handle.dataset.handle]));
    paintSong(i);
  };
  const up = () => { handle.removeEventListener('pointermove', move); handle.removeEventListener('pointerup', up); paintSong(i); };
  handle.addEventListener('pointermove', move); handle.addEventListener('pointerup', up);
});
// Keyboard: arrows move a handle by one second (shift: ten).
$('#sessionSongs').addEventListener('keydown', event => {
  const handle = event.target.closest('[data-handle]');
  if (!handle || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
  event.preventDefault();
  const i = Number(handle.closest('[data-song-wave]').dataset.songWave), songs = songList(), song = songs[i];
  const step = (event.shiftKey ? 10 : 1) * (event.key === 'ArrowLeft' ? -1 : 1);
  if (handle.dataset.handle === 'start') song.start = Math.max(i ? songs[i - 1].end : 0, Math.min(song.start + step, song.end - 1));
  else song.end = Math.min(i < songs.length - 1 ? songs[i + 1].start : fullSession.data.duration, Math.max(song.end + step, song.start + 1));
  paintSong(i);
});
$('#sessionSongs').addEventListener('input', event => {
  const row = event.target.closest('[data-session-song]'), field = event.target.dataset.songField;
  if (!row || !field) return;
  songList()[Number(row.dataset.sessionSong)][field] = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
});
addEventListener('resize', () => { if (!$('#sessionReview').hidden && fullSession.data?.songs) songList().forEach((_, i) => paintSong(i)); });

// The JM private beta reviews long concerts without forcing a 1-2 hour
// listen-all transcoding job in an HTTP HEAD request. The original owner-only
// Engine supports bounded Ogg excerpts from real tracks. Play them in
// consecutive short chunks; the entire song is still listenable, and clicking
// anywhere on its waveform loads that exact part without re-detecting songs.
const SONG_LISTEN_CHUNK_SECONDS = 45;
const SONG_LISTEN_MAX_BYTES = 12 * 1024 * 1024;

async function playSavedSongMix(i,from=null){
  stopSongPreview();
  const song=songList()[i],id=fullSession.id;
  if(!song||!id)return;
  const generation=sessionPlayer.generation;
  const alive=()=>sessionPlayer.generation===generation &&
    fullSession.id===id && sessionPlayer.index===i;
  sessionPlayer.index=i;
  const button=document.querySelector('[data-song-play="'+i+'"]');
  button?.classList.add('on','loading');
  if(button)button.textContent='■';
  try{
    let state=await api('/montara/session/'+id+'/mix-preview?song='+song.id);
    if(state.status==='not-started'||state.status==='failed'){
      state=await api('/montara/session/'+id+'/mix-preview',{song:song.id});
    }
    const started=Date.now();
    while(state.status==='rendering'){
      if(!alive())return;
      $('#sessionStatus').textContent=
        'Preparing the saved mix for the whole song (effects and panning included)…';
      // No rough fallback: that would make the saved mix sound different.
      await new Promise(resolve=>setTimeout(resolve,1300));
      state=await api('/montara/session/'+id+'/mix-preview?song='+song.id);
      if(Date.now()-started>45*60*1000)throw new Error('The saved mix is taking too long. You can retry playback.');
    }
    if(!alive())return;
    if(state.status!=='ready')throw new Error(state.error||'Could not prepare your saved mix.');
    // Download in short owner-authenticated ranges, not one large response.
    // A 16 MB MP3 crossing the HTTPS tunnel in one request can fail despite
    // already being fully rendered and saved by the private worker.
    const pieces=[];
    let total=null;
    const chunkSize=2*1024*1024;
    let loaded=0;
    const controller=new AbortController();
    sessionPlayer.controllers.add(controller);
    try{
      while(total===null||loaded<total){
        if(!alive())return;
        const end=loaded+chunkSize-1;
        const response=await fetch('/montara/session/'+id+'/mix-preview/result/'+song.id,{
          cache:'no-store',signal:controller.signal,
          headers:{Range:'bytes='+loaded+'-'+end}
        });
        if(response.status!==206)
          throw new Error('Saved mix audio range unavailable (HTTP '+response.status+').');
        if(!(response.headers.get('Content-Type')||'').startsWith('audio/mpeg'))
          throw new Error('The private mixer returned an unexpected audio format.');
        const match=/^bytes (\d+)-(\d+)\/(\d+)$/.exec(
          response.headers.get('Content-Range')||'');
        if(!match||Number(match[1])!==loaded)
          throw new Error('Saved mix audio returned an invalid byte range.');
        const size=Number(match[3]),last=Number(match[2]);
        if(size<=0||size>128*1024*1024||last<loaded||last>=size||
            (total!==null&&size!==total))
          throw new Error('Saved mix audio has inconsistent length.');
        total=size;
        const piece=await response.blob();
        if(piece.size!==last-loaded+1||piece.size>chunkSize)
          throw new Error('Saved mix audio chunk was incomplete.');
        pieces.push(piece);
        loaded=last+1;
        $('#sessionStatus').textContent='Loading saved mix audio · '+Math.round(100*loaded/total)+'%';
      }
    }finally{
      sessionPlayer.controllers.delete(controller);
    }
    const blob=new Blob(pieces,{type:'audio/mpeg'});
    if(!alive())return;
    const url=URL.createObjectURL(blob);
    sessionPlayer.urls.add(url);
    const audio=new Audio(url);
    audio.preload='metadata';
    sessionPlayer.audio=audio;
    audio.addEventListener('ended',()=>{if(alive())stopSongPreview();},{once:true});
    audio.addEventListener('error',()=>{
      if(alive())toast('The saved mix could not be decoded.',true);
    },{once:true});
    if(from!==null){
      audio.addEventListener('loadedmetadata',()=>{
        if(alive())audio.currentTime=Math.max(0,Number(from)-song.start);
      },{once:true});
    }
    await audio.play();
    if(!alive()){audio.pause();return;}
    button?.classList.remove('loading');
    $('#sessionStatus').textContent=state.source==='final'?
      'Listening to your saved final mix.':
      'Listening to your saved mix (session audio; export uses your originals).';
    const tick=()=>{
      if(!alive()||sessionPlayer.audio!==audio)return;
      const row=document.querySelector('[data-song-wave="'+i+'"]');
      if(row){
        const view=songView(i),head=row.querySelector('.song-playhead');
        if(head){
          head.hidden=false;
          head.style.left=String((song.start+audio.currentTime-view.from)/
            Math.max(.001,view.to-view.from)*row.clientWidth)+'px';
        }
      }
      sessionPlayer.raf=requestAnimationFrame(tick);
    };
    tick();
  }catch(error){
    if(!alive())return;
    stopSongPreview();
    toast(error.message||'Saved mix preview failed.',true);
  }
}

function warmSessionAudio() {
  // Deliberately no HEAD /listen: Flask would synchronously decode the whole
  // two-hour session even for HEAD, saturating the private worker's threads.
}

function stopSongPreview() {
  sessionPlayer.generation = (sessionPlayer.generation || 0) + 1;
  for (const controller of sessionPlayer.controllers || []) controller.abort();
  sessionPlayer.controllers = new Set();
  sessionPlayer.audio?.pause();
  sessionPlayer.audio = null;
  for (const url of sessionPlayer.urls || []) URL.revokeObjectURL(url);
  sessionPlayer.urls = new Set();
  cancelAnimationFrame(sessionPlayer.raf);
  document.querySelectorAll('.song-play.on, .song-play.loading').forEach(b => {
    b.classList.remove('on', 'loading'); b.textContent = '▶';
  });
  document.querySelectorAll('.song-playhead').forEach(p => { p.hidden = true; });
  const status = $('#sessionStatus');
  if (status.textContent.includes('listening excerpt')) status.textContent = '';
  sessionPlayer.index = -1;
}

async function playSong(i, from = null) {
  if (sessionPlayer.index === i && from === null) return stopSongPreview();
  stopSongPreview();
  const song = songList()[i], id = fullSession.id;
  if (!song || !id) return;
  // After a user mix exists, never silently fall back to the rough equal-
  // level boundary guide. The backend uses the same per-song DSP renderer
  // and effects as export, from already uploaded session audio.
  if(fullSession.mixes?.[song.id])return playSavedSongMix(i,from);
  const generation = sessionPlayer.generation;
  sessionPlayer.index = i;
  const button = document.querySelector(`[data-song-play="${i}"]`);
  button?.classList.add('on', 'loading');
  if (button) button.textContent = '■';
  const alive = () => sessionPlayer.generation === generation &&
    sessionPlayer.index === i && fullSession.id === id;
  const controllers = sessionPlayer.controllers;
  const urls = sessionPlayer.urls;
  let prefetched = null;

  const release = chunk => {
    if (!chunk) return;
    chunk.audio.pause();
    URL.revokeObjectURL(chunk.url);
    urls.delete(chunk.url);
  };
  const fail = error => {
    if (!alive()) return;
    stopSongPreview();
    toast(error?.message || 'Could not load this listening excerpt.', true);
  };
  const fetchChunk = async start => {
    const end = Math.min(Number(songList()[i].end),
                         Number((start + SONG_LISTEN_CHUNK_SECONDS).toFixed(2)));
    if (end - start < .5) return null;
    const controller = new AbortController();
    controllers.add(controller);
    try {
      const params = new URLSearchParams({
        start: start.toFixed(2), end: end.toFixed(2)
      });
      const response = await fetch(`/montara/session/${id}/listen?${params}`, {
        method: 'GET', cache: 'no-store', signal: controller.signal
      });
      if (!response.ok) throw new Error(
        `Could not prepare this listening excerpt (HTTP ${response.status}).`);
      if (!(response.headers.get('Content-Type') || '').startsWith('audio/ogg'))
        throw new Error('The server returned an unexpected listening format.');
      const size = Number(response.headers.get('Content-Length') || 0);
      if (size > SONG_LISTEN_MAX_BYTES)
        throw new Error('Listening excerpt is larger than the private limit.');
      const blob = await response.blob();
      if (blob.size > SONG_LISTEN_MAX_BYTES)
        throw new Error('Listening excerpt is larger than the private limit.');
      if (!alive()) return null;
      const url = URL.createObjectURL(blob);
      urls.add(url);
      const audio = new Audio(url);
      audio.preload = 'auto';
      audio.load();
      return {start, end, audio, url};
    } finally {
      controllers.delete(controller);
    }
  };

  const playChunk = async start => {
    if (!alive()) return;
    const current = prefetched?.start === start ?
      await prefetched.promise : await fetchChunk(start);
    prefetched = null;
    if (!alive()) { release(current); return; }
    if (!current) return stopSongPreview();
    const {audio} = current;
    sessionPlayer.audio = audio;
    audio.addEventListener('error', () => {
      if (alive() && sessionPlayer.audio === audio)
        fail(new Error('Could not decode the listening excerpt.'));
    }, {once: true});
    audio.addEventListener('ended', () => {
      if (!alive() || sessionPlayer.audio !== audio) return;
      release(current);
      sessionPlayer.audio = null;
      cancelAnimationFrame(sessionPlayer.raf);
      if (current.end >= songList()[i].end - .5) return stopSongPreview();
      button?.classList.add('loading');
      $('#sessionStatus').textContent = 'Loading the next listening excerpt…';
      playChunk(current.end).catch(fail);
    }, {once: true});
    try {
      await audio.play();
      if (!alive()) { release(current); return; }
      button?.classList.remove('loading');
      $('#sessionStatus').textContent = '';
      const tick = () => {
        if (!alive() || sessionPlayer.audio !== audio) return;
        const t = current.start + audio.currentTime;
        if (t >= songList()[i].end) return stopSongPreview();
        const row = document.querySelector(`[data-song-wave="${i}"]`);
        if (row) {
          const view = songView(i), head = row.querySelector('.song-playhead');
          if (head) {
            head.hidden = false;
            head.style.left =
              `${(t - view.from) / (view.to - view.from) * row.clientWidth}px`;
          }
        }
        sessionPlayer.raf = requestAnimationFrame(tick);
      };
      tick();
      if (current.end < songList()[i].end - .5) {
        // Fetch ahead while the current 45 seconds are playing; cap to one
        // extra segment and revoke it on any seek, pause or tab change.
        const promise = fetchChunk(current.end);
        promise.catch(() => {});
        prefetched = {start: current.end, promise};
      }
    } catch (error) { fail(error); }
  };
  const start = Math.max(song.start, Math.min(from ?? song.start, song.end - .5));
  $('#sessionStatus').textContent = 'Preparing a short listening excerpt…';
  try { await playChunk(start); } catch (error) { fail(error); }
}

// Click on a waveform (not on a handle): play from that point.
$('#sessionSongs').addEventListener('click', event => {
  const row = event.target.closest('[data-song-wave]');
  if (!row || event.target.closest('[data-handle]')) return;
  const i = Number(row.dataset.songWave), view = songView(i), rect = row.getBoundingClientRect();
  const t = view.from + (event.clientX - rect.left) / rect.width * (view.to - view.from);
  playSong(i, Math.max(0, Math.min(t, songList()[i].end - .2)));
});

// Mixer for one song. The first time it prepares an excerpt of the busiest part of that
// song; afterwards it reopens at once, with the changes the person saved.
fullSession.mixCache = fullSession.mixCache || {};
const songKey = song => `${fullSession.id}:${song.start}-${song.end}`;

function applySavedMix(changes) {
  if (!changes) return;
  const keys = { eq_low_cut_hz: ['low', 'hz'], eq_mid_gain_db: ['mid', 'db'], eq_air_gain_db: ['air', 'db'], eq_high_cut_hz: ['high', 'hz'] };
  for (const t of mix.plan.tracks) {
    // Reopening the Mixer on a different section must not quietly use a
    // new automatic base balance beneath the user's saved fader offsets.
    if (changes.base_gains?.[t.file] !== undefined) {
      const saved=Number(changes.base_gains[t.file]);
      t.base_gain_db=saved;
      t.auto_fader_db=saved;
      t.fader_db=saved;
    }
    if (changes.faders?.[t.file] !== undefined)
      t.fader_db=Number(t.auto_fader_db)+Number(changes.faders[t.file]);
    if (changes.mutes?.[t.file] !== undefined) t.mute = changes.mutes[t.file];
    if (changes.pans?.[t.file] !== undefined) t.pan = Number(changes.pans[t.file]);
    for (const [key, value] of Object.entries(changes.eq?.[t.file] || {})) { const [slot, field] = keys[key]; if (t.eq?.[slot]) t.eq[slot][field] = value; }
    for (const [effect, amount] of Object.entries(changes.effects?.[t.file] || {})) {
      t.fx ||= { reverb: { enabled: false, amount: 35 }, delay: { enabled: false, amount: 35 } };
      t.fx[effect] = { enabled: amount > 0, amount: amount > 0 ? Math.round(amount * 100) : t.fx[effect]?.amount ?? 35 };
    }
  }
}

async function openSongMixer(i,previewAt=null) {
  const song = songList()[i];
  if(fullSession.forVideo)fullSession.data.songs=fullSession.data.songs.map(s=>({...s,selected:s.id===song.id}));
  stopSongPreview();
  fullSession.mixSong = song.id;
  const cached = fullSession.mixCache[song.id];
  try {
    if (previewAt===null && cached && cached.key === songKey(song)) {
      Object.assign(mix, { job: cached.job, plan: cached.plan, buffers: cached.buffers, fxBuffers: cached.fxBuffers, offset: 0 });
      show('mix'); stopMix();
      renderStrips();
      $$('#strips input, #strips button').forEach((el, index) => { el.disabled = false; });
      $$('#strips .strip').forEach((strip, index) => { if (mix.plan.tracks[index].active === false) strip.querySelectorAll('input,button').forEach(el => { el.disabled = true; }); });
      $('#mixStatus').classList.add('done'); $('#transport').hidden = false; $('#referenceRow').hidden = false;
      $('#useMix').disabled = false; $('#playMix').disabled = false; $('#resetMix').disabled = false; $('#mixBack').disabled = false;
    } else {
      // The mixer screen opens now; the excerpt is cut while its faders move.
      const stop = mixLoadingScreen(fullSession.data.track_files || [], `${song.name}: preparing the busiest part of the song…`);
      let prepared;
      fullSession.cancelRequested=false;
      try { prepared = await waitSession(await sessionRequest(`/montara/session/${fullSession.id}/prepare`,
        {songs:songList(),song:song.id,...(previewAt===null?{}:{preview_at:previewAt})}));checkSessionCancel(); }
      finally { stop(); }
      fullSession.data.songs = prepared.songs.map((s, j) => ({ ...s, confirmed: songList()[j]?.confirmed }));
      await openMixer(prepared.preview_tracks);
      applySavedMix(fullSession.mixes[song.id]);
      renderStrips();
      $$('#strips .strip').forEach((strip, index) => { if (mix.plan.tracks[index].active === false) strip.querySelectorAll('input,button').forEach(el => { el.disabled = true; }); });
      fullSession.mixCache[song.id] = { key: songKey(song), job: mix.job, plan: mix.plan, buffers: mix.buffers, fxBuffers: mix.fxBuffers };
    }
    $('#useMix').textContent = fullSession.forVideo ? 'Use this mix for the video' : 'Save mix for this song';
    $('#mixAll').hidden = fullSession.forVideo; $('#mixAll').disabled = false;
    fullSession.mixPreviewAt ||= {};
    fullSession.mixPreviewAt[song.id]=previewAt;
    $('#mixAnotherSection').hidden=false;
    $('#mixStatusText').textContent = fullSession.forVideo ? 'Adjust your tracks, then use this mix as the audio for your video.' :
      `${song.name}: ${Math.ceil(mix.plan.duration)} s ${previewAt===null?'from the busiest part':'from '+clock(previewAt)}. Saved adjustments apply to this entire song.`;
  } catch (error) { toast(error.message, true); show('sessionReview'); }
}

// Audition a different moment of the song without resetting adjusted faders.
const nextMixSection=document.createElement('button');
nextMixSection.id='mixAnotherSection';
nextMixSection.type='button';
nextMixSection.className='btn ghost';
nextMixSection.textContent='Choose another section';
nextMixSection.hidden=true;
$('#mixBack').before(nextMixSection);
nextMixSection.addEventListener('click',async()=>{
  if(fullSession.busy || !fullSession.mixSong || !mix.plan?.tracks?.length)return;
  const songs=songList(),index=songs.findIndex(song=>song.id===fullSession.mixSong);
  if(index<0)return;
  const song=songs[index],last=fullSession.mixPreviewAt?.[song.id];
  const proposal=Math.min(song.end-1,(last??song.start)+Math.max(20,mix.plan.duration||45));
  const raw=window.prompt('Choose another moment of '+song.name+' (mm:ss or hh:mm:ss of concert)',clock(proposal));
  if(raw===null)return;
  const at=parseConcertSplitTime(raw);
  if(!Number.isFinite(at)||at<song.start||at>=song.end)
    return toast('Choose between '+clock(song.start)+' and '+clock(song.end),true);
  fullSession.mixes[song.id]=mixChanges();
  delete fullSession.mixCache[song.id];
  stopMix();
  nextMixSection.disabled=true;
  try{await openSongMixer(index,at);}
  finally{nextMixSection.disabled=false;}
});

$('#sessionSongs').onclick = event => {
  const master = event.target.closest('[data-song-master]');
  if (master) {
    const song=songList()[Number(master.dataset.songMaster)];
    const result=fullSession.data.results?.find(r=>r.id===song.id &&
      Math.abs(r.start-song.start)<.01 && Math.abs(r.end-song.end)<.01);
    if(!result)return toast('This song has not been mastered yet.',true);
    stopSongPreview();
    if(fullSession.finalMaster)fullSession.finalMaster.pause();
    fullSession.finalMaster=new Audio('/montara/session/'+fullSession.id+'/result/'+song.id);
    fullSession.finalMaster.play().catch(err=>toast(err.message,true));
    return;
  }
  const play = event.target.closest('[data-song-play]');
  if (play) return playSong(Number(play.dataset.songPlay));
  const confirm = event.target.closest('[data-song-confirm]');
  if (confirm) return confirmSong(Number(confirm.dataset.songConfirm));
  const mixer = event.target.closest('[data-song-mixer]');
  if (mixer) return openSongMixer(Number(mixer.dataset.songMixer));
  const split = event.target.closest('[data-song-split]'), remove = event.target.closest('[data-song-remove]');
  if (!split && !remove) return;
  const songs = songList().map(s => ({...s})), index = Number((split || remove).dataset[split ? 'songSplit' : 'songRemove']);
  if (split) {
    const song = songs[index], middle = Math.round((song.start + song.end) / 2 * 10) / 10;
    if (song.end - song.start < 2) return toast('This song is too short to split.');
    const requested = window.prompt('Split ' + song.name +
      ' at concert time (mm:ss or hh:mm:ss). Listen first; not an automatic detection.',
      clock(middle));
    if (requested === null) return;
    const splitTime = parseConcertSplitTime(requested);
    if (!Number.isFinite(splitTime) || splitTime <= song.start + 1 || splitTime >= song.end - 1) {
      return toast('Choose a time between ' + clock(song.start + 1) +
        ' and ' + clock(song.end - 1) + '.', true);
    }
    songs.splice(index, 1, {...song, end: splitTime, confirmed: false}, {...song, id: undefined, start: splitTime, name: `${song.name} · 2`, confirmed: false});
  } else songs.splice(index, 1);
  // Songs are numbered by position on the server: keep each saved mix with its song.
  const mixes = {};
  songs.forEach((song, j) => { if (song.id !== undefined && fullSession.mixes[song.id]) mixes[j + 1] = fullSession.mixes[song.id]; song.id = j + 1; });
  fullSession.mixes = mixes;
  drawSessionSongs(songs);
};

$('#sessionMix').onclick = () => {
  if(!fullSession.forVideo)return renderFullSession();
  const selected=songList().filter(song=>song.selected);
  if(selected.length!==1)return toast('Choose one song for this video.',true);
  return openSongMixer(songList().findIndex(song=>song.id===selected[0].id));
};

// A track detection found empty can be brought back (the excerpts are cut again).
$('#sessionEmpty').addEventListener('click', async event => {
  const button = event.target.closest('[data-include-track]');
  if (!button) return;
  button.disabled = true;
  try {
    const data = await api(`/montara/session/${fullSession.id}/include`, { file: button.dataset.includeTrack });
    fullSession.data.empty_tracks = data.empty_tracks; fullSession.mixCache = {};
    drawSessionSongs();
  } catch (error) { button.disabled = false; toast(error.message, true); }
});

// The changes made in the mixer, relative to its automatic mix: nothing else travels.
function mixChanges() {
  const changes = {
    faders: Object.fromEntries(mix.plan.tracks.map(t => [t.file, Number(t.fader_db || 0) - Number(t.auto_fader_db ?? t.fader_db ?? 0)]).filter(([, v]) => Math.abs(v) > .05)),
    mutes: Object.fromEntries(mix.plan.tracks.filter(t => Boolean(t.mute) !== Boolean(t.auto_mute ?? t.mute)).map(t => [t.file, Boolean(t.mute)])),
  };
  // Store the EXACT automatic audible level (auto makeup + auto fader).
  // The render engine accepts a makeup baseline and a manual fader offset.
  // Omitting the second automatic level term made voices, bass and drums
  // drift even though the user's fader moves were applied correctly.
  // The new full-song DSP uses the effective automatic gain as its frozen
  // baseline, then applies only the manually changed fader difference.
  changes.base_gains=Object.fromEntries(mix.plan.tracks.map(t=>[
    t.file,Number(t.auto_fader_db||0)]));
  // Explicitly include OFF for every channel: the browser preview has no
  // hidden automatic reverb/delay. The final DSP must disable vendor sends
  // that the user never heard, and mix only the effects they switched ON.
  changes.effects=Object.fromEntries(mix.plan.tracks.map(t=>[
    t.file,Object.fromEntries(['reverb','delay'].map(key=>[key,
      t.fx?.[key]?.enabled?Number(t.fx[key].amount)/100:0]))]));
  const eq = eqChanges();
  if (Object.keys(eq).length) changes.eq = eq;
  const pans = Object.fromEntries(mix.plan.tracks
    .filter(t=>Math.abs(Number(t.pan||0)-Number(t.auto_pan??t.pan??0))>.005)
    .map(t=>[t.file,Number(t.pan)]));
  if(Object.keys(pans).length)changes.pans=pans;
  return changes;
}

// "Save mix for this song" in the mixer: keep the changes, back to the list.
// The same changes on every song (each keeps its own automatic mix underneath).
$('#mixAll').addEventListener('click',async()=>{
  if(fullSession.busy)return;
  stopMix();
  const changes=mixChanges(),songs=songList();
  const button=$('#mixAll');button.disabled=true;
  try{
    const current=await api('/montara/mix/'+mix.job);
    if(current?.reference)changes.reference=current.reference;
    for(const song of songs){
      const saved=await sessionRequest('/montara/session/'+fullSession.id+'/save-mix',
        {song:song.id,window:[song.start,song.end],mix:changes});
      fullSession.mixes[song.id]=saved.saved_song_mixes[String(song.id)];
      if(changes.reference)fullSession.mixes[song.id].reference=changes.reference;
    }
    show('sessionReview');drawSessionSongs();
    toast('Mix settings saved for all '+songs.length+' songs.');
  }catch(error){toast('Could not save every song: '+error.message,true);}
  finally{button.disabled=false;}
});

async function saveSongMix(){
  if(!fullSession.mixSong||!mix.plan?.tracks)return;
  const song= songList().find(item=>item.id===fullSession.mixSong);
  if(!song)return toast('Song selection changed. Reopen its Mixer.',true);
  stopMix();
  const changes=mixChanges(),job=mix.job;
  const button=$('#useMix');button.disabled=true;
  try{
    const reference=await api('/montara/mix/'+job);
    if(reference?.reference)changes.reference=reference.reference;
    // Preserve the exact user settings on the server BEFORE leaving the
    // mixer. Neither Confirm nor Ready can silently revert to rough audio.
    const saved=await sessionRequest('/montara/session/'+fullSession.id+'/save-mix',
      {song:song.id,window:[song.start,song.end],mix:changes});
    fullSession.mixes[song.id]=saved.saved_song_mixes[String(song.id)];
    if(changes.reference)fullSession.mixes[song.id].reference=changes.reference;
    fullSession.data.results=saved.results||[];
    if(fullSession.forVideo){
      show('sessionReview');drawSessionSongs();
      return renderFullSession(true);
    }
    show('sessionReview');
    drawSessionSongs();
    toast('Mix saved. Play uses your processed audio, not the rough listening guide.');
  }catch(error){
    toast('Mix was not saved: '+error.message,true);
  }finally{button.disabled=false;}
}

async function renderFullSession(forVideo = false) {
  if(fullSession.cancelling)return;
  stopSongPreview();
  const songs = songList();
  if (!songs.some(s => s.selected)) return toast('Select at least one song.', true);
  if (songs.filter(s => s.selected).length > 30) return toast('Choose at most 30 songs.',true);
  if(forVideo && songs.filter(s=>s.selected).length!==1)return toast('Choose one song for this video.',true);
  if (!confirmLongSongReview(songs)) return;
  $('#sessionMix').hidden = true;
  fullSession.cancelRequested = false;
  fullSession.exportRun = (fullSession.exportRun || 0) + 1;
  fullSession.localProgress = {};
  fullSession.localResults = [];
  clearSessionResults();
  fullSession.data.results = [];
  showSessionProgress({...fullSession.data, status: 'rendering', results: [], render_progress: {}});
  try {
    // Save the boundaries first: the original ranges and the per-song mixes follow them.
    const saved = await sessionRequest(`/montara/session/${fullSession.id}/songs`, { songs });
    fullSession.data.songs = saved.songs.map((s, j) => ({ ...s, confirmed: songs[j]?.confirmed }));
    const ids = new Set(saved.songs.map(s => String(s.id)));
    const per_song = Object.fromEntries(Object.entries(fullSession.mixes).filter(([id]) => ids.has(String(id))));
    // Mixing starts at once: each song begins on the server as soon as its original ranges
    // arrive, while this computer keeps sending the next ones.
    // With the companion's local mixer, songs are mixed on this computer and only the MP3
    // travels; any song it cannot do (reference, no original here, error) goes to the server.
    const selected = saved.songs.filter(s => s.selected);
    const serverSongs = await mixSongsLocally(selected, per_song);
    if (fullSession.cancelRequested) { showSessionProgress({...fullSession.data, status: 'cancelled'}); return; }
    const started = await sessionRequest(`/montara/session/${fullSession.id}/render`, { songs: saved.songs, per_song, long_songs_reviewed: true });
    for (const song of serverSongs){checkSessionCancel();await queueSongOriginals(song);}
    const data = await waitSession(started);
    checkSessionCancel();
    if (forVideo) {
      const song = data.songs.find(s=>s.selected);
      const master = await api(`/montara/session/${fullSession.id}/video-master`, {song:song.id});
      state.mixMaster = master.master;
      state.mixDownload=`/montara/session/${fullSession.id}/result/${song.id}?download=1`;
      fullSession.active = false;
      range.start = 0; range.end = null;
      await registerProject({mixed:true});
      return;
    }
    $('#sessionStatus').textContent = data.status==='partial' ?
      data.error || 'Some songs failed; completed masters are ready.' :
      'Your selected songs are ready.';
    if(data.status==='partial')toast($('#sessionStatus').textContent,true);
    drawSessionResults(data);
    drawSessionSongs();
  } catch (error) {
    if(!fullSession.cancelRequested){
      showSessionProgress({...fullSession.data,status:'failed',error:error.message});
      toast(error.message,true);
    }
  }
  finally { fullSession.busy = false; $('#sessionBack').disabled = false; $('#sessionCancel').hidden = true; $('#sessionMix').hidden = false; }
}

// ---------- songs mixed on this computer (companion local mixer) ----------
// Returns the songs the server still has to mix.
async function mixSongsLocally(songs, perSong) {
  if (!fullSession.data.uses_previews) return songs;
  await montaraCompanion.detect();   // the companion may have been started (or updated) since the page loaded
  checkSessionCancel();
  const mixer = montaraCompanion.localMixer();
  if (!mixer) return songs;
  const left = [], uploads = [];
  let warned = false;
  for (const song of songs) {
    if (fullSession.cancelRequested) break;
    const mix = perSong[song.id] || {};
    // Local Companion does not yet attest the saved per-song baseline/pan
    // protocol. Never silently discard one of these controls in an export.
    if (mix.reference || Object.keys(mix.base_gains||{}).length ||
        Object.keys(mix.pans||{}).length) { left.push(song); continue; }   // mastering references are mixed on the server
    $('#sessionStatus').textContent = fullSession.forVideo ? 'Mixing and mastering your song…' : 'Mixing songs…';
    fullSession.localProgress[song.id] = {status: 'working', progress: 0, tracks: []};
    paintSessionRender(fullSession.data);
    $('#sessionWorking').hidden = false;
    try {
      const query = new URLSearchParams({ song: song.id, start: song.start, end: song.end, name: song.name || '' });
      const plan = await api(`/montara/session/${fullSession.id}/local-plan?${query}`);
      checkSessionCancel();
      if (plan.mixer !== mixer) {
        if (!warned) console.info('Companion mixer version differs; using the server.');
        warned = true; left.push(song);
        delete fullSession.localProgress[song.id]; continue;
      }
      fullSession.localProgress[song.id].tracks = plan.tracks.map(t => ({file: t.file, progress: 0, active: true}));
      paintSessionRender(fullSession.data);
      fullSession.mixAbort=new AbortController();
      fullSession.mixPromise=montaraCompanion.mixSong(plan, mix, progress => {
        if(fullSession.cancelRequested)return;
        fullSession.localProgress[song.id] = progress;
        paintSessionRender(fullSession.data);
      },fullSession.mixAbort.signal);
      const {blob,seconds}=await fullSession.mixPromise;
      checkSessionCancel();
      const name = `${(song.name || 'Song').replace(/[^\w .-]/g, '_')}.mp3`;
      // The next song is mixed while this MP3 uploads.
      uploads.push((async () => {
        let uploadId = null;
        await sendResumableUpload(new File([blob], name, { type: 'audio/mpeg' }), () => {}, id => { uploadId = id; },()=>fullSession.cancelRequested);
        checkSessionCancel();
        await sessionRequest(`/montara/session/${fullSession.id}/local-result`, { song: song.id, window: plan.window, upload_id: uploadId, mixer: plan.mixer, seconds, mix });
        fullSession.localProgress[song.id] = {status: 'ready', progress: 1, tracks: plan.tracks.map(t => ({file: t.file, progress: 1}))};
        fullSession.localResults.push(song);
        drawSessionResults({results: fullSession.localResults}, {[song.id]: blob});
        paintSessionRender(fullSession.data);
      })().catch(error => { if(!fullSession.cancelRequested){console.warn('local result upload failed', error); left.push(song);} }));
    } catch (error) {
      if(fullSession.cancelRequested)break;
      console.warn('local mix failed', song.name, error);
      if (!warned) toast('Retrying the mix…');
      warned = true; left.push(song);
      delete fullSession.localProgress[song.id];
    }
  }
  await Promise.all(uploads);
  return songs.filter(song => left.includes(song));
}

// ---------- original ranges, sent in the background ----------
// Tracks sent as light previews: the export uses the originals, but only the song ranges.
// A confirmed song starts sending at once, while the person keeps editing the others.
const uploader = { queue: [], seen: new Set(), running: false, done: 0, total: 0, bytes: 0, started: 0, byWindow: {} };
const windowKey = song => `${Number(song.start).toFixed(3)}-${Number(song.end).toFixed(3)}`;

// Queue the original ranges of one song window. Ranges belong to their window, never to a song
// number, so a split or a removed song never invalidates what is already queued or sent.
async function queueSongOriginals(song) {
  const query = new URLSearchParams({ song: song.id, start: song.start, end: song.end, name: song.name || '' });
  const { originals } = await api(`/montara/session/${fullSession.id}/originals?${query}`);
  const tally = uploader.byWindow[windowKey(song)] ||= { done: 0, total: 0 };
  for (const w of originals) {
    const key = `${w.file}@${w.window.join('-')}`;
    if (uploader.seen.has(key)) continue;
    uploader.seen.add(key); tally.total++;
    if (w.received) { tally.done++; continue; }
    uploader.queue.push(w); uploader.total++;
  }
  paintUploadState();
  runUploader();
}

async function runUploader() {
  if (uploader.running) return;
  uploader.running = true; fullSession.sending = true;
  uploader.started ||= performance.now();
  const failed = [];
  let inARow = 0;
  try {
    while (uploader.queue.length) {
      const w = uploader.queue.shift();
      paintUploadState(w);
      try {
        const fast = montaraCompanion.canFastSegments();
        const blob = await montaraCompanion.segment(w.original, w.start, w.duration, fast ? 'opus' : 'lossless');
        uploader.bytes += blob.size;
        // Fast: Opus; lossless: FLAC, or WavPack for float originals (FLAC has no float).
        const ext = blob.type === 'audio/ogg' ? '.wav.hq.opus' : blob.type === 'audio/x-wavpack' ? '.wav.wv' : '.wav.flac';
        const name = `${w.file.replace(/\.wav$/i, '')}${ext}`;
        let uploadId = null;
        await sendResumableUpload(new File([blob], name, { type: blob.type || 'audio/flac' }), () => {}, id => { uploadId = id; });
        await api(`/montara/session/${fullSession.id}/originals`, { song: w.song, window: w.window, file: w.file, upload_id: uploadId });
        uploader.done++; inARow = 0;
        const tally = uploader.byWindow[w.window.map(Number).map(v => v.toFixed(3)).join('-')];
        if (tally) tally.done++;
        paintUploadState();
      } catch (error) {
        // One range failing never drops the rest of the queue; it is retried on the next export.
        failed.push(w); uploader.seen.delete(`${w.file}@${w.window.join('-')}`); uploader.total--;
        console.warn('original range failed', w.file, w.window, error);
        if (++inARow >= 3) { failed.push(...uploader.queue); for (const q of uploader.queue) uploader.seen.delete(`${q.file}@${q.window.join('-')}`); uploader.total -= uploader.queue.length; uploader.queue = []; toast(`Original audio stopped: ${error.message}. Keep Montara and the companion open, then export again.`, true); }
      }
    }
    if (failed.length && inARow < 3) toast(`${failed.length} original range${failed.length > 1 ? 's' : ''} could not be sent; they are retried when you export.`, true);
  } finally {
    uploader.running = false; fullSession.sending = false;
    paintUploadState();
  }
}

function paintUploadState(current = null) {
  const line = $('#sessionUpload');
  if (!line) return;
  line.textContent = '';
  (fullSession.data?.songs || []).forEach((song, i) => paintConfirm(i));
}

// The Confirm control of one song: Confirm → Confirming… → Confirmed · Sending n/m → Confirmed · Ready.
function paintConfirm(i) {
  const song = songList()[i], tag = document.querySelector(`[data-confirm-state="${i}"]`), button = document.querySelector(`[data-song-confirm="${i}"]`);
  if (!song || !tag || !button) return;
  const tally = uploader.byWindow[windowKey(song)];
  button.hidden = Boolean(song.confirmed || song.confirming);
  tag.classList.toggle('done', Boolean(song.confirmed));
  tag.textContent = song.confirming ? 'Confirming…' : !song.confirmed ? ''
    : !tally || !tally.total || tally.done >= tally.total ? (tally?.total ? 'Confirmed · ready' : 'Confirmed')
    : `Confirmed · sending ${tally.done}/${tally.total}`;
}

// Confirm: these cuts are final, start sending this song's original ranges now. Nothing is
// saved on the server and nothing else stops (playback, other uploads): the window is enough.
async function confirmSong(i) {
  const song = songList()[i];
  if (!song || song.confirming || song.confirmed) return;
  song.confirming = true; paintConfirm(i);
  try {
    await queueSongOriginals(song);
    song.confirmed = true;
  } catch (error) { toast(error.message, true); }
  finally { song.confirming = false; paintConfirm(i); }
}

// One thick bar per song, then a fine row of stems for each song. Progress comes
// from completed extraction steps and the mixer's processed audio chunks.
function paintSessionRender(data) {
  const songs = (data.songs || []).filter(s => s.selected);
  const visible = songs.length && ['rendering','done','partial','failed'].includes(data.status);
  $('#sessionRender').hidden = !visible;
  if (!visible) return;
  $('#sessionHint').hidden = true;
  $('#sessionProgress').hidden = true;
  $('#sessionEta').textContent = '';
  const completed = new Set([...(data.results || []), ...(fullSession.localResults || [])].map(s => String(s.id)));
  const states = {...fullSession.localProgress, ...data.render_progress};
  const signature = JSON.stringify(songs.map(s => [s.id, s.name, (states[s.id]?.tracks || data.track_files || []).map(t => t.file || t)]));
  if ($('#sessionRender').dataset.signature !== signature) {
    $('#sessionRender').dataset.signature = signature;
    $('#sessionBars').innerHTML = songs.map(s => `<i data-render-song="${s.id}" role="progressbar" aria-label="${escapeHtml(s.name)}" aria-valuemin="0" aria-valuemax="100"></i>`).join('');
    $('#sessionTrackBars').innerHTML = songs.map(s => `<div data-track-song="${s.id}">${(states[s.id]?.tracks || data.track_files || []).map(t => `<i role="progressbar" aria-label="${escapeHtml(s.name)} · ${escapeHtml(t.file || t)}" aria-valuemin="0" aria-valuemax="100"></i>`).join('')}</div>`).join('');
  }
  function paint(bar, value, active, label) {
    value = Math.max(0, Math.min(1, Number(value) || 0));
    bar.style.setProperty('--p', value);
    bar.classList.toggle('active', Boolean(active && value < 1));
    bar.classList.toggle('complete', value >= 1);
    bar.setAttribute('aria-valuenow', Math.round(value * 100));
    bar.title = `${label} · ${Math.round(value * 100)}%`;
  }
  for (const song of songs) {
    const state = states[song.id] || {}, mixed = completed.has(String(song.id));
    const entry = sessionResultCache.get(`${fullSession.id}:${fullSession.exportRun || 0}:${song.id}:${song.start}:${song.end}`);
    const ready = mixed && entry?.loaded;
    // 100% means the MP3 is available, not merely that its DSP has ended.
    const fraction = ready ? 1 : mixed ? .95 + .049 * (entry?.progress || 0) : Math.min(.94, state.progress || 0);
    const active = !mixed && state.status === 'working';
    const eta = state.elapsed && fraction > .25 && fraction < .9 ? ` · ≈${clock(state.elapsed * (1 - fraction) / fraction)}` : '';
    paint($(`[data-render-song="${song.id}"]`), fraction, active || (mixed && !ready), song.name + eta);
    const bars = document.querySelector(`[data-track-song="${song.id}"]`).children;
    [...bars].forEach((bar, i) => {
      const track = state.tracks?.[i];
      paint(bar, mixed ? 1 : Math.min(.99, track?.progress || 0), active && track?.active, bar.getAttribute('aria-label'));
    });
  }
}

const sessionResultCache = new Map();
function clearSessionResults() {
  for (const entry of sessionResultCache.values()) {
    entry.controller.abort();
    entry.audio.pause();
    if (entry.url) URL.revokeObjectURL(entry.url);
  }
  sessionResultCache.clear();
  $('#sessionResults').replaceChildren();
}

function drawSessionResults(data, blobs = {}) {
  const container = $('#sessionResults'), session = fullSession.id;
  const songs = [...(data.results || [])].sort((a, b) => a.start - b.start);
  for (const song of songs) {
    const key = `${session}:${fullSession.exportRun || 0}:${song.id}:${song.start}:${song.end}`;
    if (sessionResultCache.has(key)) continue;  // never restart a playing/preloading song at a poll
    const row = document.createElement('div'); row.className = 'session-song session-result';
    row.dataset.result = String(song.id);
    const name = document.createElement('b'); name.textContent = song.name;
    const loading = document.createElement('button'); loading.className = 'song-play loading';
    loading.type = 'button'; loading.disabled = true; loading.textContent = '▶';
    loading.setAttribute('aria-label', `Loading ${song.name}`);
    const fill = document.createElement('progress'); fill.max = 1; fill.value = 0;
    fill.setAttribute('aria-label', `Loading ${song.name}`);
    const audio = document.createElement('audio'); audio.controls = true; audio.preload = 'auto'; audio.hidden = true;
    const link = document.createElement('a'); link.className = 'btn ghost small'; link.textContent = 'Download';
    link.href = `/montara/session/${session}/result/${song.id}?download=1`; link.download = '';
    row.append(name, loading, fill, audio, link);
    const after = [...container.querySelectorAll('.session-result')].find(r => Number(r.dataset.start) > song.start);
    row.dataset.start = song.start;
    container.insertBefore(row, after || container.querySelector('.session-download-all'));
    const entry = {audio, controller: new AbortController(), url: null, loaded: false, progress: 0};
    sessionResultCache.set(key, entry);
    const prepare = async () => {
      loading.disabled = true; loading.classList.add('loading');
      fill.hidden = false;
      try {
        let blob = blobs[song.id];
        if (!blob) {
          const response = await fetch(`/montara/session/${session}/result/${song.id}?v=${fullSession.exportRun || 0}`, {signal: entry.controller.signal, cache: 'no-store'});
          if (!response.ok) throw new Error('Could not load this song.');
          const total = Number(response.headers.get('Content-Length'));
          const reader = response.body.getReader(), chunks = []; let bytes = 0;
          for (;;) {
            const {done, value} = await reader.read(); if (done) break;
            chunks.push(value); bytes += value.byteLength;
            if (total) { fill.value = bytes / total; entry.progress = fill.value; } else fill.removeAttribute('value');
            paintSessionRender(fullSession.data);
          }
          blob = new Blob(chunks, {type: 'audio/mpeg'});
        }
        if (entry.controller.signal.aborted) return;
        entry.url = URL.createObjectURL(blob);
        // Only attach a complete local blob: play can no longer outrun the network.
        audio.src = entry.url; audio.load();
        entry.loaded = true; entry.progress = 1;
        audio.hidden = false; loading.hidden = true; fill.hidden = true;
        paintSessionRender(fullSession.data);
      } catch (error) {
        if (entry.controller.signal.aborted) return;
        loading.disabled = false; loading.classList.remove('loading'); loading.textContent = '↻';
        loading.setAttribute('aria-label', `Retry loading ${song.name}`); fill.hidden = true;
        loading.onclick = prepare;
      }
    };
    prepare();
  }
  let all = container.querySelector('.session-download-all');
  if (container.querySelectorAll('.session-result').length > 1) {
    if (!all) {
      all = document.createElement('div'); all.className = 'session-song session-download-all';
      all.innerHTML = `<a class="btn primary small" href="/montara/session/${session}/results.zip" download>Download all</a>`;
      container.append(all);
    }
  }
}

// Keep the exact session through a refresh; no rerun of detection or mixing.
addEventListener('pagehide',()=>{
  try {if(fullSession.active && fullSession.id)sessionStorage.setItem('montara-open-session',fullSession.id);else sessionStorage.removeItem('montara-open-session');} catch {}
});
document.addEventListener('DOMContentLoaded',()=>{
  try {if(sessionStorage.getItem('montara-open-session') && !sessionStorage.getItem('montara-open-edit')){
    clearTimeout(introTimer);state.platform='youtube';$('#sessionResume').click();
  }} catch {}
});
