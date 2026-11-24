'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('web/montara.js','utf8');
const start=source.indexOf('async function api(path, body)');
const end=source.indexOf('\nfunction showPausedPreview()',start);
assert.ok(start >= 0 && end > start,'real browser api function is present');
function mount(fetcher) {
  const ctx=vm.createContext({
    fetch:fetcher,
    TypeError,
    console:{warn:()=>{}},
    location:{hostname:'montara-lab-fer.memoriainvalida001.workers.dev'},
    setTimeout:(fn)=>fn(),
  });
  return vm.runInContext(source.slice(start,end)+';api',ctx);
}
test('Owner preflight rejection remains visible instead of masquerading as /montara/uploads network loss',async()=>{
  let count=0;
  const api=mount(async()=>{count++;throw new Error('Private Engine unavailable');});
  await assert.rejects(api('/montara/uploads'),/Private Engine unavailable/);
  assert.equal(count,1,'do not retry a semantic owner gateway failure');
});
test('expired Owner session remains visible instead of generic upload disconnection',async()=>{
  const api=mount(async()=>{throw new Error('Montara session expired');});
  await assert.rejects(api('/montara/uploads'),/Montara session expired/);
});
test('true read-only network failure retries boundedly; POST network failure never retries',async()=>{
  let reads=0;
  const a=mount(async()=>{reads++;throw new TypeError('Failed to fetch');});
  await assert.rejects(a('/montara/uploads'),/Lost the connection to Montara/);
  assert.equal(reads,3);
  let writes=0;
  const b=mount(async()=>{writes++;throw new TypeError('Failed to fetch');});
  await assert.rejects(b('/montara/uploads',{name:'test'}),/Lost the connection to Montara/);
  assert.equal(writes,1,'never replay an upload initialization POST');
});
test('Owner gateway JSON errors preserve error string and status fallback',async()=>{
  const a=mount(async()=>({ok:false,status:503,json:async()=>({error:'Private Engine unavailable'})}));
  await assert.rejects(a('/montara/uploads'),/Private Engine unavailable/);
  const b=mount(async()=>({ok:false,status:502,json:async()=>({})}));
  await assert.rejects(b('/montara/uploads'),/Request failed \(502\)/);
});
test('file failure has display priority over Companion-derived ready labels',()=>{
  const stateStart=source.indexOf('f.kind === "uploading" ? (f.phase');
  assert.ok(stateStart >= 0);
  const excerpt=source.slice(stateStart,source.indexOf('</span>',stateStart));
  const errorAt=excerpt.indexOf('f.kind === "error"');
  const previewAt=excerpt.indexOf('f.preview ? "Ready · preview"');
  const smallAt=excerpt.indexOf('f.small ? "Ready · lossless"');
  assert.ok(errorAt >= 0 && previewAt > errorAt && smallAt > errorAt);
  assert.ok(!excerpt.slice(errorAt+1).includes('f.kind === "error" ?'));
});
