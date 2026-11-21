'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const types=fs.readFileSync(__dirname+'/../web/track-types.js','utf8');
const ui=fs.readFileSync(__dirname+'/../web/montara.js','utf8');
const a=ui.indexOf('const MixerChannels =');
const b=ui.indexOf('async function openMixer(',a);
const p=ui.indexOf('function stereoPairs(tracks)');
const q=ui.indexOf('function applyGain(track)',p);
assert(a>0 && b>a && p>b && q>p);
const context={document:{addEventListener(){}},console};
vm.createContext(context);
vm.runInContext(types+';globalThis.tt=TrackTypes',context);
vm.runInContext(ui.slice(a,b)+';globalThis.mc=MixerChannels',context);
const items=[
 ['2310112026Kick Int4tinsel.tracks.wav','kick','Kick In','drums'],
 ['2310112026Kick outt4tinsel.tracks.wav','kick','Kick Out','drums'],
 ['2310112026HHt4tinsel.tracks.wav','hh','Hi-hat','drums'],
 ['2310112026Snaret4tinsel.tracks.wav','snare','Snare','drums'],
 ['2310112026Tom 2t4tinsel.tracks.wav','drums','Tom 2','drums'],
 ['2310112026OVt4tinsel.tracks.wav','overhead','Overhead','drums'],
 ['2310112026Basst4tinsel.tracks.wav','bass','Bass','bass'],
 ['2310112026Guitt4tinsel.tracks.wav','guitar_electric','Guitar','guitars'],
 ['2310112026Keyst4tinsel.tracks.wav','keys','Piano / Keys','keys'],
 ['2310112026Syntht4tinsel.tracks.wav','synth','Synth','keys'],
 ['2310112026Chemat4tinsel.tracks.wav','vocal','Chema','voices'],
 ['2310112026Janoscht4tinsel.tracks.wav','vocal','Janosch','voices'],
];
for(const [file,role,label,family] of items){
 const track={file,role,active:true};
 assert.equal(context.tt.guess(file),role,file);
 assert.equal(context.mc.short(track),label,file);
 assert.equal(context.mc.family(track),family,file);
}
const ordered=context.mc.sort([items[10],items[6],items[0],items[11],items[3],items[7]]
  .map(([file,role])=>({file,role,active:true})));
assert.equal(context.mc.family(ordered[0]),'drums');
assert.equal(context.mc.family(ordered[2]),'bass');
assert.equal(context.mc.family(ordered.at(-1)),'voices');
context.tt.set(items[10][0],{type:'bass'});
assert.equal(context.mc.family({file:items[10][0],role:'vocal'}),'bass');
const wave=[
 {file:'Kick.wav',role:'kick',active:true},
 {file:'Snare.wav',role:'snare',active:true},
 {file:'Keys L.wav',role:'keys_l',active:true},
 {file:'Keys R.wav',role:'keys_r',active:true},
 {file:'Lead Vocal.wav',role:'vocal',active:true},
 {file:'Backing Vocal.wav',role:'vocal',active:true},
];
context.wave=wave;
vm.runInContext('mix.groupLinks={stereo:true,drums:false,voices:false};mix.plan={tracks:wave}',context);
vm.runInContext(ui.slice(p,q)+';globalThis.peers=mixerPeers',context);
assert.equal(context.peers(wave[0]).length,1);
vm.runInContext('mix.groupLinks.drums=true',context);
assert.equal(context.peers(wave[0]).length,2);
vm.runInContext('mix.groupLinks.drums=false',context);
assert.equal(context.peers(wave[0]).length,1);
assert.equal(context.peers(wave[2]).length,2);
vm.runInContext('mix.groupLinks.stereo=false',context);
assert.equal(context.peers(wave[2]).length,1);
vm.runInContext('mix.groupLinks.voices=true',context);
assert.equal(context.peers(wave[4]).length,2);
vm.runInContext('mix.groupLinks.voices=false',context);
assert.equal(context.peers(wave[4]).length,1);
console.log('MIXER_CHANNEL_GROUPS_PASS 12_instruments_manual_override_stereo_drums_voices_link_unlink');
