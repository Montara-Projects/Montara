'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const source=fs.readFileSync('web/full-session.js','utf8');

test('music full-session JavaScript parses',()=>new vm.Script(source));
test('unchecked song can open mixer without changing export checkbox',()=>{
  const mixer=source.slice(source.indexOf('async function openSongMixer('),
    source.indexOf("$('#sessionSongs').onclick ="));
  assert.ok(mixer.startsWith('async function openSongMixer('));
  assert.ok(!mixer.includes('if(fullSession.forVideo)fullSession.data.songs=fullSession.data.songs.map'));
  assert.match(mixer,/const originals=songList\(\)\.map\(s=>\(\{\.\.\.s\}\)\)/);
  assert.match(mixer,/const previewSongs=originals\.map\(s=>\(\{\.\.\.s,selected:s\.id===song\.id\}\)\)/);
  assert.match(mixer,/songs: previewSongs, song: song\.id/);
  assert.match(mixer,/selected:originals\[j\]\?\.selected===true/);
  assert.match(mixer,/confirmed:originals\[j\]\?\.confirmed===true/);
  assert.match(mixer,/fullSession\.mixCache\[song\.id\]/);
});
test('Confirm selects exactly its song explicitly, not on Mixer entry',()=>{
  const confirm=source.slice(source.indexOf('async function confirmSong('),
    source.indexOf('// One thick bar',source.indexOf('async function confirmSong(')));
  assert.match(confirm,/song\.selected=true/);
  assert.match(confirm,/checkbox\.checked=true/);
  assert.match(confirm,/await queueSongOriginals\(song\)/);
});
test('video export commits selection only when using its mix',()=>{
  const save=source.slice(source.indexOf('async function saveSongMix('),
    source.indexOf('async function renderFullSession('));
  assert.match(save,/if\(fullSession\.forVideo\)\{/);
  assert.match(save,/s\.selected=String\(s\.id\)===String\(songId\)/);
  assert.match(save,/return renderFullSession\(true\)/);
});
test('final export is still blocked with no explicitly selected songs',()=>{
  assert.match(source,/if \(!songs\.some\(s => s\.selected\)\) return toast\('Select at least one song\.'/);
});
