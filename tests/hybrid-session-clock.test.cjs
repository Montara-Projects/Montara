const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const hybrid=require('../web/hybrid-stage-contract.js');
const dual=require('../web/hybrid-session-clock.js');
const selection=vm.runInNewContext(fs.readFileSync('web/sync-selection.js','utf8')+';SyncSelection');
const video=vm.runInNewContext(fs.readFileSync('web/session-video.js','utf8')+';SessionVideo');
const id='87a5e63d37b7';
const duration=14248.1;
const clock=()=>dual.timeline({sessionId:id,fullDurationSec:duration,cropStartSec:2235,cropDurationSec:1062});
const clips=()=>({one:{source_path:'cameraA',path:'cameraA',duration_sec:762,offset_sec:150.2563,confidence:34.564,unstable_sync:false,low_confidence:false,verification:{checked:true,unstable_sync:false,consensus_count:3}}});
const projected=()=>hybrid.project({fullMasterDurationSec:duration,cropStartSec:2235,cropDurationSec:1062,clips:clips()});
test('B10 dual clock preserves full 4h duration and 18min short sync window',()=>{
 const c=clock();assert.equal(c.ok,true);assert.equal(c.global_duration_sec,14248.1);
 assert.equal(c.sync_window.start_sec,2235);assert.equal(c.sync_window.end_sec,3297);
 assert.equal(c.stage_ready,false);assert.match(c.stage_blocker,/global master/i);
});
test('real B5 projected camera matches global Stage excerpt, not crop-local time',()=>{
 const p=projected();
 const c=clock();
 const song=video.excerptForClips(c.global_duration_sec,p.projected_clips);
 assert.ok(Math.abs(song.start-2385.2563)<.0001);
 const result=dual.prepareExcerpt(c,p,p.projected_clips,song);
 assert.equal(result.ok,true);assert.equal(result.stage_ready,false);
 assert.equal(result.excerpt_global.start_sec,song.start);
 assert.equal(result.sync_reference.start_sec,2235);
 assert.equal(selection.windowCoverage([{path:'cameraA'}],p.projected_clips,{start:2386,end:2400}).covered,true);
 assert.equal(result.listening.stage_master,false);
});
test('listening request is bounded and uses the real existing endpoint only',()=>{
 const r=dual.rangeRequest(clock(),2385.2563,2450);
 assert.equal(r.ok,true);assert.equal(r.kind,'bounded_listening_only');
 assert.ok(r.url.startsWith('/montara/session/'+id+'/listen?start='));
 assert.equal(r.stage_master,false);assert.equal(r.global_end_sec,2450);
});
test('no invented four-hour audio: existing full-guide flag does not create Stage readiness',()=>{
 const c=dual.timeline({sessionId:id,fullDurationSec:duration,cropStartSec:2235,cropDurationSec:1062,fullGuideAvailable:true});
 assert.equal(c.stage_ready,false);assert.equal(dual.prepareExcerpt(c,projected(),projected().projected_clips,{start:2385.2563,end:2450}).ok,false);
});
test('invalid IDs and missing/corrupt global durations fail-closed',()=>{
 for(const bad of ['../../etc/passwd','ff000','00000000000G',null])
  assert.equal(dual.timeline({sessionId:bad,fullDurationSec:duration,cropStartSec:2235,cropDurationSec:1062}).reason,'invalid_session_identity');
 for(const args of [{fullDurationSec:-1},{cropStartSec:-1},{cropDurationSec:15000},{cropDurationSec:0}])
  assert.equal(dual.timeline({sessionId:id,fullDurationSec:duration,cropStartSec:2235,cropDurationSec:1062,...args}).ok,false);
});
test('audio-only is never redirected through experimental video planner',()=>{
 assert.equal(dual.timeline({sessionId:id,mode:'audio',fullDurationSec:duration,cropStartSec:2235,cropDurationSec:1062}).reason,'audio_only_pipeline_unchanged');
});
test('listening rejects beyond global duration, negative or greater than 1h',()=>{
 const c=clock();
 for(const [a,b] of [[-1,100],[14000,15000],[10,10.2],[0,4000],[300,290]])
  assert.equal(dual.rangeRequest(c,a,b).reason,'invalid_listening_range');
});
test('wrong master duration, discontinuous gap and failed Engine evidence never create a plan',()=>{
 const c=clock(),p=projected(),s={start:2386,end:2400};
 assert.equal(dual.prepareExcerpt(c,{...p,master_duration_sec:1062},p.projected_clips,s).ok,false);
 assert.equal(dual.prepareExcerpt(c,p,p.projected_clips,{start:15000,end:15020}).ok,false);
 const discontinuous=hybrid.project({fullMasterDurationSec:duration,cropStartSec:2235,cropDurationSec:1062,clips:{one:{...clips().one,offset_ranges:[{clip_start_sec:20,clip_end_sec:30,offset_sec:150.2563}]}}});
 assert.equal(selection.windowCoverage([{path:'cameraA'}],discontinuous.projected_clips,{start:2450,end:2470}).covered,false);
 assert.equal(dual.prepareExcerpt(c,{ok:false}, {},s).ok,false);
});
test('no global sync result is confused with a Stage master asset',()=>{
 const c=clock(),p=projected();
 const song=video.excerptForClips(c.global_duration_sec,p.projected_clips);
 const r=dual.prepareExcerpt(c,p,p.projected_clips,song);
 assert.equal(r.stage_ready,false);
 assert.equal(r.listening.stage_master,false);
 assert.equal('master' in r,false);
 assert.ok(r.requires.some(x=>x.includes('wizard')));
});