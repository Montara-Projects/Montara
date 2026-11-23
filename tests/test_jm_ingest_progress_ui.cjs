'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const test=require('node:test');
const source=fs.readFileSync('web/montara.js','utf8');
test('current Stage JavaScript parses',()=>new vm.Script(source));
test('measured per-video bars retained; giant third bar not mounted',()=>{
  const start=source.indexOf('function updateIngestIndicator(');
  const end=source.indexOf('class WorkCancelled',start);
  const block=source.slice(start,end);
  assert.match(block,/holder\.append\(label,meta,taskList\)/);
  assert.doesNotMatch(block,/holder\.append\(label,bar,percent,meta,taskList\)/);
  assert.match(block,/bar\.hidden=true/);
  assert.match(block,/percent\.hidden=true/);
  assert.match(block,/info\.taskList\.replaceChildren\(\)/);
  assert.match(block,/const line=document\.createElement\('progress'\)/);
  assert.match(block,/info\.taskList\.append\(row\)/);
  assert.match(block,/info\.meta\.textContent=/);
});
test('overall real wizard ring and Continue safeguards unchanged',()=>{
  const html=fs.readFileSync('web/index.html','utf8');
  assert.match(html,/class="ring"/);
  assert.match(html,/id="ringBar"/);
  assert.match(source,/\$\("#continueFootage"\)\.disabled = !ready/);
  assert.match(source,/if \(state\.uploads\) return toast\('Wait for the files to finish preparing\.'/);
});
