'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(__dirname+'/../web/montara.js','utf8');
const begin=source.indexOf('const FULL_SESSION_TRACK_LIMIT = 16;');
const end=source.indexOf('// An untouched tab does not keep the VM alive;',begin);
assert(begin>0 && end>begin);
const snippet=source.slice(begin,end);
const file=name=>({name,size:1024,lastModified:1});
function harness({existing=0,task='session',sample=false}={}) {
  const files=Array.from({length:existing},(_,i)=>({id:String(i),name:`stem${i}.wav`,kind:'uploading'}));
  if(sample)files.push({id:'sample',name:'demo.wav',kind:'songs',sample:true});
  const state={platform:'youtube',audioTask:task,files};
  const elements={'#fullSessionOn':{checked:task==='session'},'#sampleNote':{},'#restoreNote':{}};
  const uploads=[],warnings=[];let renders=0;
  const context={state,crypto:{randomUUID:()=>String(Math.random())},
    '$':k=>elements[k],rejectRaw360:()=>false,
    isAudioEntry:f=>f.kind==='songs'||f.kind==='master'||(/\.(wav|mp3|m4a|aiff?|flac|ogg)$/i.test(f.name)&&f.kind!=='video'),
    remember:()=>{},upload:(f,e)=>uploads.push({f,e}),
    renderFiles:()=>renders++,toast:(message)=>warnings.push(message)};
  vm.createContext(context);
  vm.runInContext(snippet+';globalThis.runAdd=addFiles;globalThis.testFull=fullSessionTrackSelection;',context);
  return {context,state,uploads,warnings,get renders(){return renders;}};
}
test('15 pending tracks + three selected: only one upload starts, existing 15 survive',()=>{
  const h=harness({existing:15});h.context.runAdd([file('a.wav'),file('b.flac'),file('c.ogg')]);
  assert.equal(h.uploads.length,1);assert.equal(h.state.files.length,16);
  assert(h.state.files.slice(0,15).every(f=>f.kind==='uploading'));
  assert.match(h.warnings[0],/2 extra tracks were skipped/);
});
test('full session at 16 declines the next track without modifying uploads',()=>{
  const h=harness({existing:16});const before=[...h.state.files];
  h.context.runAdd([file('extra.wav')]);
  assert.equal(h.uploads.length,0);assert.deepEqual(h.state.files,before);
  assert.match(h.warnings[0],/1 extra track was skipped/);
  assert.equal(h.renders,1);
});
test('non-session mode never imposes global audio track ceiling',()=>{
  const h=harness({existing:16,task:'song'});h.context.runAdd([file('extra.wav')]);
  assert.equal(h.uploads.length,1);assert.equal(h.state.files.length,17);
  assert.equal(h.warnings.length,0);
});
test('example tracks are replaced, do not consume slots',()=>{
  const h=harness({existing:15,sample:true});h.context.runAdd([file('last.wav')]);
  assert.equal(h.uploads.length,1);assert.equal(h.state.files.length,16);
  assert(!h.state.files.some(f=>f.sample));
});
test('counter includes in-flight audio and only appears in full session',()=>{
  assert.match(source,/Full session · \$\{state\.files\.filter\(isAudioEntry\)\.length\}\/\$\{FULL_SESSION_TRACK_LIMIT\} audio tracks selected/);
  assert.match(source,/\$\('#audioSub'\)\.textContent=fullSessionTrackSelection\(\)/);
});
