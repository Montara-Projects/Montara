'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const src=fs.readFileSync(__dirname+'/../web/full-session.js','utf8');
const begin=src.indexOf('function installRequiredProjectName(){');
assert(begin>0);
test('Project Name placeholder, no visible title, and Continue rejects blank/whitespace',async()=>{
  const hooks={}, calls=[];
  const field={value:'',placeholder:'',required:false,
    setAttribute:(name,value)=>{calls.push([name,value]);},
    addEventListener:(name,handler)=>{hooks['field-'+name]=handler;},
    closest:()=>label,focus:()=>calls.push('focused')};
  const label={childNodes:[{nodeType:3,textContent:'Project name '},{nodeType:1}]};
  const button={disabled:false};
  const ctx={
    Node:{TEXT_NODE:3},
    document:{getElementById:id=>id==='videoName'?field:id==='continueFootage'?button:id==='footage'?{hidden:false}:null,
      addEventListener:(name,handler,capture)=>{hooks[name+(capture?'-capture':'')]=handler;}},
    state:{projectId:null},
    renderFiles:()=>{calls.push('render');button.disabled=false;},
    registerProject:async()=>{calls.push('registered');},
    toast:message=>{calls.push(message);},
    queueMicrotask:fn=>fn()
  };
  vm.createContext(ctx);
  vm.runInContext(src.slice(begin)+';globalThis.install=installRequiredProjectName;',ctx);
  ctx.install();
  assert.equal(field.placeholder,'Project Name');
  assert.equal(field.required,true);
  assert.equal(label.childNodes[0].textContent,'');
  assert.equal(button.disabled,true);
  await ctx.registerProject();
  assert(calls.includes('Enter a Project Name before continuing.'));
  assert(!calls.includes('registered'));
  field.value='    ';hooks['field-input']();
  assert.equal(button.disabled,true);
  field.value='Tales For The Tillerman';hooks['field-input']();
  assert.equal(button.disabled,false);
  await ctx.registerProject();assert(calls.includes('registered'));
  field.value='Some date';
  hooks.click({target:{closest:sel=>sel.includes('[data-audio-task]')?{}:null}});
  assert.equal(field.value,'','new project must not pre-fill a date');
});
