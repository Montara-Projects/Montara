'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../web/montara.js'),'utf8');
const a=source.indexOf('function ingestProgressModel(');
const b=source.indexOf('const ingestIndicator=',a);
assert.ok(a>=0 && b>a,'Expected pure measured progress formatter');
const model=vm.runInNewContext('('+source.slice(a,b)+')');
const now=1730000000;

const initial=model(null,3,0,0,now);
assert.equal(initial.active,false);
assert.equal(initial.percent,null);
assert.match(initial.detail,/elapsed 0:00/);

const unmeasured=model({status:'running',stage:'ingest',progress:8,stage_progress:0,tasks:[]},2,24,0,now);
assert.equal(unmeasured.active,true);
assert.equal(unmeasured.percent,null,'Global wizard progress cannot become a fabricated ingest percent');
assert.match(unmeasured.detail,/2 videos/);
assert.match(unmeasured.detail,/0:24/);

const measured=model({
  stage:'ingest',status:'running',progress:4.4,
  stage_progress:35,progress_updated_at:now-3,
  tasks:[
    {id:'proxy-0',label:'Proxy: camera 1',percent:100},
    {id:'proxy-1',label:'Proxy: camera 2',percent:47},
    {id:'prepared-0',label:'Prepared: camera 1',percent:100},
  ]
},3,83,0,now);
assert.equal(measured.percent,35,'Use measured stage value, not global wizard value');
assert.match(measured.detail,/proxies ready 1/);
assert.match(measured.detail,/analyzed 1/);
assert.match(measured.detail,/Proxy: camera 2/);
assert.match(measured.detail,/1:23/);

const noRollback=model({
  stage:'ingest',status:'running',progress:6,stage_progress:8,
  progress_updated_at:now,
},3,85,35,now);
assert.equal(noRollback.percent,35,'Concurrent progress cannot move the bar backwards');

const stillRunning=model({
  stage:'ingest',status:'running',stage_progress:100,progress_updated_at:now-50,
},3,90,0,now);
assert.equal(stillRunning.percent,99,'Do not claim complete while stage running');
assert.match(stillRunning.detail,/waiting for engine update/);

const notIngest=model({
  stage:'sync',status:'running',stage_progress:90,progress_updated_at:now,
},3,90,0,now);
assert.equal(notIngest.active,false);
assert.equal(notIngest.percent,null);

const invalid=model({
  stage:'ingest',status:'running',stage_progress:'80',progress_updated_at:now,
},3,90,0,now);
assert.equal(invalid.percent,null,'Reject string progress/approximation');

assert.match(source,/info\.bar\.removeAttribute\('value'\)/,'Unknown progress must be indeterminate');
assert.match(source,/updateIngestIndicator\(s\)/,'renderStatus should update the visual');
assert.match(source,/if \(platform === 'youtube' \|\| platform === 'reel'\)initIngestIndicator\(\)/,'Visible from Continue');
assert.ok(!source.includes('setInterval(updateIngestIndicator'), 'No new polling');
console.log('JM_348_INGEST_PROGRESS_PASS real percent, honest indeterminate, monotonic, counts, elapsed, stall, stage reset');
