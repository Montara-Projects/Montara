const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const hybrid=require('../web/hybrid-stage-contract.js');
const selection=vm.runInNewContext(fs.readFileSync('web/sync-selection.js','utf8')+';SyncSelection');
const video=vm.runInNewContext(fs.readFileSync('web/session-video.js','utf8')+';SessionVideo');
const base={fullMasterDurationSec:14248.1,cropStartSec:2235,cropDurationSec:1062};
const clip=(offset=150.2563,extra={})=>({
  source_path:'camera1',path:'camera1',duration_sec:762,offset_sec:offset,
  confidence:34.564,low_confidence:false,unstable_sync:false,
  verification:{checked:true,unstable_sync:false,consensus_count:3},...extra
});
test('B5 observed offset 2385.2563 is projected to the real four-hour clock',()=>{
 const r=hybrid.project({...base,clips:{one:clip()}});
 assert.equal(r.ok,true);assert.ok(Math.abs(r.projected_clips.one.offset_sec-2385.2563)<1e-6);
 assert.equal(r.master_duration_sec,14248.1);assert.equal(r.ready_for_stage,false);
 assert.equal(selection.review([{path:'camera1'}],r.projected_clips,{end:r.master_duration_sec}).ready.length,1);
 const song=video.excerptForClips(r.master_duration_sec,r.projected_clips);
 assert.ok(Math.abs(song.start-2385.2563)<.0001);
 assert.ok(Math.abs(song.end-(2385.2563+762))<.0001);
});
test('offset ranges are reprojected individually and gaps remain uncovered',()=>{
 const r=hybrid.project({...base,clips:{one:clip(150,{offset_ranges:[
  {clip_start_sec:20,clip_end_sec:30,offset_sec:150},
  {clip_start_sec:70,clip_end_sec:80,offset_sec:151}
 ]})}});
 assert.equal(r.ok,true);
 const c=r.projected_clips.one;assert.equal(c.offset_ranges[0].offset_sec,2385);
 assert.equal(c.offset_ranges[1].offset_sec,2386);
 const files=[{path:'camera1'}];
 assert.equal(selection.windowCoverage(files,r.projected_clips,{start:2406,end:2410}).covered,true);
 assert.equal(selection.windowCoverage(files,r.projected_clips,{start:2430,end:2440}).covered,false);
 assert.equal(selection.windowCoverage(files,r.projected_clips,{start:2457,end:2461}).covered,true);
});
test('multiple independent verified cameras remain distinct',()=>{
 const r=hybrid.project({...base,clips:{a:clip(),b:{...clip(250),source_path:'camera2',path:'camera2',duration_sec:250}}});
 assert.equal(r.ok,true);
 assert.equal(Object.keys(r.projected_clips).length,2);
 assert.equal(selection.review([{path:'camera1'},{path:'camera2'}],r.projected_clips,{end:14248.1}).ready.length,2);
});
test('no false promotion for an Engine negative even with high raw score',()=>{
 for(const changed of [
  {confidence:19.34,unstable_sync:true,verification:{checked:true,unstable_sync:true,consensus_count:1}},
  {confidence:999,low_confidence:true},
  {confidence:999,verification:{checked:false,unstable_sync:false,consensus_count:3}},
  {confidence:999,verification:{checked:true,unstable_sync:false,consensus_count:1}},
  {confidence:2},
  {no_audio:true},
  {error:'Unrelated source'}
 ]) assert.equal(hybrid.project({...base,clips:{one:clip(150,changed)}}).reason,'unproven_engine_sync');
});
test('window boundaries, invalid master metadata and source cannot be silently overwritten',()=>{
 for(const changed of [{cropStartSec:-1},{cropStartSec:14000},{cropDurationSec:0},{fullMasterDurationSec:0}])
  assert.equal(hybrid.project({...base,...changed,clips:{one:clip()}}).ok,false);
 assert.equal(hybrid.project({...base,clips:{one:clip(2500)}}).reason,'no_crop_overlap');
 assert.equal(hybrid.project({...base,clips:{one:clip(150,{source_path:''})}}).reason,'invalid_clip_metadata');
});
test('invalid or discontinuous offset ranges must not fall back to scalar coverage',()=>{
 assert.equal(hybrid.project({...base,clips:{one:clip(150,{offset_ranges:[{clip_start_sec:50,clip_end_sec:20,offset_sec:150}]})}}).reason,'invalid_offset_ranges');
 assert.equal(hybrid.project({...base,clips:{one:clip(150,{offset_ranges:[
  {clip_start_sec:0,clip_end_sec:20,offset_sec:3000}
 ]})}}).reason,'no_crop_overlap');
});
test('negative global offset is supported only when there is overlap',()=>{
 const r=hybrid.project({fullMasterDurationSec:360,cropStartSec:0,cropDurationSec:120,
   clips:{a:clip(-5,{duration_sec:20})}});
 assert.equal(r.ok,true);assert.equal(r.projected_clips.a.offset_sec,-5);
 const bad=hybrid.project({fullMasterDurationSec:360,cropStartSec:0,cropDurationSec:120,
   clips:{a:clip(-70,{duration_sec:20})}});
 assert.equal(bad.reason,'no_global_master_coverage');
});
test('no partial results when one camera has no reliable sync',()=>{
 const r=hybrid.project({...base,clips:{good:clip(),bad:{...clip(250),source_path:'camera2',confidence:11,unstable_sync:true}}});
 assert.equal(r.ok,false);assert.equal(r.projected_clips,undefined);
});