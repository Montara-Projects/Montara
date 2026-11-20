'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const full=fs.readFileSync(__dirname+'/../web/full-session.js','utf8');
const bridge=fs.readFileSync(__dirname+'/../urano/native_owner_browser_bridge.js','utf8');
function slice(begin,end) {
 const a=full.indexOf(begin);const b=full.indexOf(end,a);
 assert(a>=0&&b>a,begin);
 return full.slice(a,b);
}
const tracks=[
 {file:'Voice.wav',base_gain_db:3,auto_fader_db:2,fader_db:-8,
  pan:-.8,auto_pan:.25,mute:false,auto_mute:false,fx:{
    reverb:{enabled:true,amount:72},delay:{enabled:false,amount:30}}},
 {file:'Guitar.wav',base_gain_db:-2,auto_fader_db:-4,fader_db:-4,
  pan:.3,auto_pan:.3,mute:true,auto_mute:false,fx:{
    reverb:{enabled:false,amount:32},delay:{enabled:false,amount:20}}},
];
const ctx={mix:{plan:{tracks}},eqChanges:()=>({}),console};
vm.createContext(ctx);
vm.runInContext(slice('function mixChanges() {','// "Save mix for this song"')+
 ';globalThis.changes=mixChanges',ctx);
const values=ctx.changes();
assert.equal(values.faders['Voice.wav'],-10);
assert.equal(values.base_gains['Voice.wav'],2);
assert.equal(values.base_gains['Guitar.wav'],-4);
assert.equal(values.effects['Voice.wav'].reverb,.72);
assert.equal(values.effects['Voice.wav'].delay,0);
assert.equal(values.effects['Guitar.wav'].reverb,0);
assert.equal(values.effects['Guitar.wav'].delay,0);
assert.equal(values.pans['Voice.wav'],-.8);
assert.equal(values.pans['Guitar.wav'],undefined);
assert.equal(values.mutes['Guitar.wav'],true);
const apply=slice('function applySavedMix(changes) {','async function openSongMixer(');
const reset={file:'Voice.wav',base_gain_db:5,auto_fader_db:12,fader_db:12,
  pan:.25,auto_pan:.25,mute:false,auto_mute:false,fx:{
    reverb:{enabled:false,amount:35},delay:{enabled:false,amount:30}}};
ctx.mix={plan:{tracks:[reset]}};
vm.runInContext(apply+';globalThis.restore=applySavedMix',ctx);
ctx.restore(values);
assert.equal(reset.base_gain_db,2,'the exact audible baseline stays frozen');
assert.equal(reset.auto_fader_db,2,'new instrument analysis must not replace the audible baseline');
assert.equal(reset.fader_db,-8,'saved fader offset remains relative to original balance');
assert.equal(reset.pan,-.8);
assert.equal(reset.fx.reverb.enabled,true);
assert.equal(reset.fx.reverb.amount,72);
assert.equal(reset.fx.delay.enabled,false);
const start=bridge.indexOf('const sessionAllowed = (path, method, params) => {');
const end=bridge.indexOf('const mixAllowed =',start);
assert(start>0&&end>start);
const c={URLSearchParams};
vm.createContext(c);
vm.runInContext(bridge.slice(start,end)+';globalThis.allow=sessionAllowed',c);
const root='/montara/session/aaaaaaaaaaaa';
for(const [method,path,query] of [
 ['POST',root+'/save-mix',''],
 ['POST',root+'/mix-preview',''],
 ['GET',root+'/mix-preview','song=1'],
 ['GET',root+'/mix-preview/result/4','']]){
 assert.equal(c.allow(path,method,new URLSearchParams(query)),true,method+' '+path);
}
for(const [method,path,query] of [
 ['GET',root+'/mix-preview',''],
 ['GET',root+'/mix-preview','song=1&song=2'],
 ['POST',root+'/save-mix','song=4'],
 ['GET',root+'/mix-preview/result/0',''],
 ['HEAD',root+'/mix-preview/result/1','']
]){
 assert.equal(c.allow(path,method,new URLSearchParams(query)),false,method+' '+path);
}
assert(full.includes('if(fullSession.mixes?.[song.id])return playSavedSongMix(i,from)'));
assert(!slice('async function playSavedSongMix(i,from=null){',
              'function warmSessionAudio()').includes('/listen?'),
              'saved user mix must never silently load the raw listening guide');
console.log('SAVED_MIX_BROWSER_PARITY_PASS base_gain_fx_pan_mute_save_restore_private_routes');
