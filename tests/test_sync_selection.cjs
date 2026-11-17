const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');const fs=require('node:fs');
const policy=vm.runInNewContext(fs.readFileSync('web/sync-selection.js','utf8')+';SyncSelection');
test('silent footage is separate from uncertain cameras; filler does not need sync',()=>{
 const files=[{path:'silent'},{path:'wrong'},{path:'good'},{path:'chosen',usage:'filler'}];
 const result=policy.review(files,{a:{source_path:'silent',no_audio:true},b:{source_path:'wrong',offset_sec:0,duration_sec:20,confidence:30,unstable_sync:true},c:{source_path:'good',offset_sec:10,duration_sec:20}});
 assert.deepEqual(Array.from(result.ready,x=>x.path),['good']);
 assert.deepEqual(Array.from(result.silent,x=>x.path),['silent']);
 assert.deepEqual(Array.from(result.uncertain,x=>x.path),['wrong']);
});
test('high confidence cannot rescue nonoverlap, missing results or invalid times',()=>{
 const result=policy.review([{path:'outside'},{path:'missing'},{path:'nan'}],{a:{source_path:'outside',offset_sec:70,duration_sec:10,confidence:99},b:{source_path:'nan',offset_sec:NaN,duration_sec:10}},{end:30});
 assert.equal(result.uncertain.length,3);assert.equal(result.ready.length,0);
});

test('FER real incident: trim 98–132s does not overlap camera offset 207s',()=>{
 const clips={one:{source_path:'video',offset_sec:207.1219954648526,
  duration_sec:326.133333,confidence:29.324572,low_confidence:false}};
 const files=[{path:'video'}];
 assert.equal(policy.windowCoverage(files,clips,{start:97.913912,end:132.256273}).covered,false);
 assert.equal(policy.windowCoverage(files,clips,{start:220,end:250}).covered,true);
});
test('preflight respects camera eligibility and fillers',()=>{
 const clips={a:{path:'bad',offset_sec:50,duration_sec:40,unstable_sync:true},
  b:{path:'good',offset_sec:70,duration_sec:20}};
 assert.equal(policy.windowCoverage([{path:'bad'},{path:'good'}],clips,{start:80,end:85}).covered,true);
 assert.equal(policy.windowCoverage([{path:'bad'},{path:'filler',usage:'filler'}],clips,{start:80,end:85}).covered,false);
});
test('preflight validates window and overlap boundary',()=>{
 const clips={a:{path:'video',offset_sec:20,duration_sec:10}},files=[{path:'video'}];
 assert.equal(policy.windowCoverage(files,clips,{start:10,end:10}).valid,false);
 assert.equal(policy.windowCoverage(files,clips,{start:0,end:20.5}).covered,false);
 assert.equal(policy.windowCoverage(files,clips,{start:0,end:20.6}).covered,true);
 assert.equal(policy.windowCoverage(files,clips,{start:30,end:40}).covered,false);
});

test('confirmed discontinuous ranges reject uncovered gaps and scalar-only false positives',()=>{
 const clips={a:{source_path:'video',offset_sec:100,duration_sec:100,
  offset_ranges:[{clip_start_sec:20,clip_end_sec:30,offset_sec:100},
                 {clip_start_sec:70,clip_end_sec:80,offset_sec:100}]}};
 const files=[{path:'video'}];
 assert.equal(policy.windowCoverage(files,clips,{start:121,end:125}).covered,true);
 assert.equal(policy.windowCoverage(files,clips,{start:171,end:175}).covered,true);
 assert.equal(policy.windowCoverage(files,clips,{start:140,end:145}).covered,false);
 assert.equal(policy.windowCoverage(files,clips,{start:105,end:115}).covered,false);
 assert.equal(policy.windowCoverage(files,clips,{start:129.8,end:130.2}).covered,false);
 assert.equal(policy.windowCoverage(files,clips,{start:100,end:190}).available.length,2);
 assert.equal(policy.review(files,clips,{start:140,end:145}).ready.length,0);
 assert.equal(policy.review(files,clips,{start:171,end:175}).ready.length,1);
});
test('confirmed clip-local ranges use master offset, including negative offsets',()=>{
 const clips={a:{source_path:'video',offset_sec:-10,duration_sec:60,
  offset_ranges:[{clip_start_sec:40,clip_end_sec:50,offset_sec:-10}]}};
 const files=[{path:'video'}];
 assert.equal(policy.windowCoverage(files,clips,{start:31,end:35}).covered,true);
 assert.equal(policy.windowCoverage(files,clips,{start:41,end:45}).covered,false);
 assert.equal(policy.windowCoverage(files,clips,{start:0,end:20}).covered,false);
});
test('invalid confirmed range records fall back to scalar like Engine; ineligible cameras do not count',()=>{
 const files=[{path:'valid'},{path:'weak'},{path:'silent'}];
 const clips={
   a:{path:'valid',offset_sec:10,duration_sec:20,
      offset_ranges:[{clip_start_sec:40,clip_end_sec:20,offset_sec:10}]},
   b:{path:'weak',offset_sec:10,duration_sec:20,unstable_sync:true},
   c:{path:'silent',offset_sec:10,duration_sec:20,no_audio:true}
 };
 assert.equal(policy.windowCoverage(files,clips,{start:12,end:18}).covered,true);
 assert.equal(policy.windowCoverage(files.slice(1),clips,{start:12,end:18}).covered,false);
 assert.equal(policy.review(files,clips,{start:12,end:18}).ready.length,1);
});
