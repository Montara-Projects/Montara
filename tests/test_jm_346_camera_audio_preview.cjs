'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../web/montara.js'), 'utf8');
const from = source.indexOf('function cameraAudioPreviewSources(');
const to = source.indexOf('\nfunction openSongRange()', from);
assert.ok(from >= 0 && to > from, 'Keep the camera-preview selection function testable');
const select = vm.runInNewContext('(' + source.slice(from, to) + ')');
const proxy = {size: 12_000_000,type:'video/mp4'};
const cameras = [
  {name:'C0020',kind:'video',path:'/owner/Uploads/video-1',cameraProxyAudioFile:proxy},
  {name:'insert',kind:'video',usage:'filler',path:'/owner/Uploads/video-2',cameraProxyAudioFile:proxy},
  {name:'missing',kind:'video',path:'/owner/Uploads/video-3'},
  {name:'audio',kind:'master',path:'/owner/Uploads/master',cameraProxyAudioFile:proxy}
];
const preview = select(cameras,false);
assert.equal(preview.length,1);
assert.equal(preview[0].cameraEntry,cameras[0]);
assert.match(preview[0].name,/preview only/);
assert.equal(select(cameras,true).length,0,'Never audition camera audio when an actual master exists');
assert.ok(source.includes('cameraAudioProxyBytes+small.file.size<=MAX_CAMERA_AUDIO_PROXY_TOTAL'));
assert.ok(source.includes('!state.mixMaster && !audioTracks().length'));
assert.ok(source.includes('state.files.forEach(releaseCameraAudioPreview)'));
console.log('JM_346_CAMERA_AUDIO_PREVIEW_PASS camera-only fallback, master isolated, bounded memory, cleanup');
