const assert=require('node:assert/strict');
const fs=require('fs');
const vm=require('vm');
const {test}=require('node:test');
const source=fs.readFileSync(__dirname+'/../web/full-session.js','utf8');
const saveBody=source.slice(source.indexOf('async function saveSongMix(){'),
  source.indexOf('\nasync function renderFullSession(',source.indexOf('async function saveSongMix(){')));
test('Save mix preserves settings and does not compete with Mixer using full-song render',async()=>{
  const calls=[];
  const session={id:'abc123abc123',mixSong:3,forVideo:false,
    mixes:{},data:{results:[]}};
  const nodes=new Map();
  const $=key=>{
    if(!nodes.has(key))nodes.set(key,{disabled:false});
    return nodes.get(key);
  };
  const ctx={
    fullSession:session,
    songList:()=>[{id:3,start:0,end:409}],
    mix:{job:'a'.repeat(12),plan:{tracks:[{file:'voice.wav'}]}},
    stopMix(){},
    mixChanges:()=>({faders:{'voice.wav':-4},effects:{'voice.wav':{reverb:.4}}}),
    api:async path=>({reference:null}),
    sessionRequest:async(path,data)=>{
      calls.push(path);
      if(path.endsWith('/save-mix'))
        return {saved_song_mixes:{'3':data.mix},results:[]};
      throw Error('Unexpected request '+path);
    },
    show:()=>{},drawSessionSongs:()=>{},
    toast:()=>{},$
  };
  vm.createContext(ctx);
  vm.runInContext(saveBody+'\nthis.saveSongMix=saveSongMix;',ctx);
  await ctx.saveSongMix();
  assert.deepEqual(calls,['/montara/session/abc123abc123/save-mix']);
  assert.equal(session.mixes[3].faders['voice.wav'],-4);
  assert.equal($('#useMix').disabled,false);
});
