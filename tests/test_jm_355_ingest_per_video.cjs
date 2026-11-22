'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const code=fs.readFileSync(path.join(__dirname,'../web/montara.js'),'utf8');
const css=fs.readFileSync(path.join(__dirname,'../web/montara.css'),'utf8');
const start=code.indexOf('function ingestVideoTasks(');
const stop=code.indexOf('\nfunction initIngestIndicator()',start);
assert.ok(start>0&&stop>start,'Per-video model present');
const model=vm.runInNewContext('('+code.slice(start,stop)+')');
const now=1730000000;
const base=[
 {id:'proxy-0',label:'Proxy 1',percent:100},
 {id:'prepared-0',label:'Prepared 1',percent:100},
 {id:'proxy-1',label:'Proxy 2',percent:100},
 {id:'proxy-2',label:'Proxy 3',percent:100},
 {id:'proxy-3',label:'Proxy 4',percent:8},
 {id:'proxy-4',label:'Proxy 5',percent:100}
];
const first=model({stage:'ingest',status:'running',stage_progress:81,progress_updated_at:now-5,tasks:base},5,now);
assert.equal(first.items.length,5);
assert.equal(first.items[0].phase,'Video ready');
assert.equal(first.items[0].done,true);
assert.equal(first.items[1].phase,'Proxy prepared');
assert.equal(first.items[1].active,false,'A completed proxy should not spin');
assert.equal(first.items[3].percent,8,'Actual proxy progress 8%; not global 81%');
assert.equal(first.items[3].active,true);
assert.equal(first.items[3].phase,'Preparing proxy');

const later=model({
  stage:'ingest',status:'running',stage_progress:81,progress_updated_at:now-4,
  tasks:[...base.slice(0,4),{id:'proxy-3',label:'Proxy 4',percent:12},...base.slice(5)]
},5,now);
assert.equal(later.items[3].percent,12,'Proxy advances 8 to 12 while global remains at 81');
assert.equal(first.items[3].percent,8,'Earlier snapshot remains unaffected');
assert.equal(later.items[3].active,true);

const analyzing=model({
  stage:'ingest',status:'running',progress_updated_at:now-6,
  tasks:[{id:'proxy-3',percent:100},{id:'framing-3',percent:23}]
},5,now);
assert.equal(analyzing.items[3].phase,'Analyzing framing');
assert.equal(analyzing.items[3].percent,23,'Phase percent, never falsely aggregate');

const stale=model({
  stage:'ingest',status:'running',progress_updated_at:now-130,
  tasks:[{id:'proxy-3',percent:14}]
},5,now);
assert.equal(stale.fresh,false);
assert.equal(stale.items[3].active,false);
assert.equal(stale.age,130,'No motor heartbeat should be invented');
assert.equal(stale.items[2].percent,null,'Unknown progress stays indeterminate');

const invalid=model({
  stage:'ingest',status:'running',progress_updated_at:now,
  tasks:[{id:'proxy-3',percent:'91'}, {id:'proxy-2',percent:134}, {id:'proxy-1',percent:-25}, {id:'proxy-500',percent:50}]
},5,now);
assert.equal(invalid.items[3].percent,null,'Reject strings');
assert.equal(invalid.items[2].percent,100,'Clamp invalid high to 100');
assert.equal(invalid.items[1].percent,0,'Clamp invalid negative to 0');
assert.equal(invalid.items.length,5,'Bound generated rows');

const many=model({stage:'ingest',status:'running',progress_updated_at:now,tasks:[]},90,now);
assert.equal(many.items.length,40,'Bound DOM rows');
assert.equal(many.more,50,'Show extra count without lying');

assert.match(css,/--accent:#FF4F2E/);
assert.match(css,/#ingestMeasuredProgress progress\s*\{/);
assert.match(css,/accent-color:var\(--accent\)/);
assert.match(css,/#ingestMeasuredProgress progress::-webkit-progress-value/);
assert.match(css,/#ingestMeasuredProgress progress::-moz-progress-bar/);
assert.match(css,/@media\(prefers-reduced-motion:reduce\)/);
assert.match(code,/info\.taskList\.append\(row\)/);
assert.match(code,/line\.value=task\.percent/);
assert.ok(!code.includes('setInterval(updateIngestIndicator'),'No extra server polling');
console.log('JM_355_PER_VIDEO_PROGRESS_PASS orange cross-browser, five sources, global plateau 81, proxy 8→12, analysis phase, stale honest, bounded DOM');
