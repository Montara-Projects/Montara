const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const script=fs.readFileSync(require('node:path').join(__dirname,'../web/montara.js'),'utf8');
const begin=script.indexOf('function canonicalProjectTitle(value) {');
const end=script.indexOf('async function registerProject({mixed',begin);
assert.ok(begin>0 && end>begin);
const source=script.slice(begin,end)+'\nthis.select=selectCanonicalVideoProject;';
function init({id=null,shelf=[],active=null,name='Song',opened='/owner/one.zuckervid'}={}) {
  const requests=[];
  const state={projectId:id};
  const api=async (url,body)=>{
    requests.push([url,body]);
    if(url==='/project')return {name};
    if(url==='/wizard/status')return {project_path:active};
    if(url==='/wizard/projects')return {projects:shelf};
    if(url==='/wizard/projects/open')return {project_path:opened};
    if(url==='/wizard/projects/new')return {ok:true};
    throw Error('Unexpected '+url);
  };
  const context=vm.createContext({state,api,Error,String,Map});
  vm.runInContext(source,context);
  return {select:context.select,requests};
}
(async()=>{
  const a=init({id:'/owner/one.zuckervid',active:'/owner/one.zuckervid'});
  assert.equal(await a.select(' Song '),'/owner/one.zuckervid');
  assert.ok(!a.requests.some(r=>r[0].endsWith('/new')));
  const b=init({shelf:[{path:'/owner/one.zuckervid',name:'  SONG '} ]});
  assert.equal(await b.select('song'),'/owner/one.zuckervid');
  assert.ok(b.requests.some(r=>r[0]==='/wizard/projects/open'));
  assert.ok(!b.requests.some(r=>r[0]==='/wizard/projects/new'));
  const c=init({shelf:[]});
  assert.equal(await c.select('Brand New'),null);
  assert.ok(c.requests.some(r=>r[0]==='/wizard/projects/new'));
  const d=init({shelf:[{path:'/a',name:'song'},{path:'/b',name:'SONG'}]});
  await assert.rejects(()=>d.select('song'),/Several saved projects/);
  assert.ok(!d.requests.some(r=>r[0]==='/wizard/projects/new'));
  const e=init({id:'/owner/old',active:'/owner/other'});
  await assert.rejects(()=>e.select('song'),/Another project/);
  assert.ok(!e.requests.some(r=>r[0]==='/wizard/projects/new'));
  const f=init({id:'/owner/old',active:'/owner/old',name:'Other'});
  await assert.rejects(()=>f.select('song'),/Renaming must be explicit/);
  console.log('CANONICAL_VIDEO_SELECTION_PASS 6 scenarios');
})().catch(err=>{console.error(err);process.exitCode=1;});
