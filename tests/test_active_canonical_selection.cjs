const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const script=fs.readFileSync(require('node:path').join(__dirname,'../ops/jm/canonical-projects-380/active_web_montara.js'),'utf8');
const begin=script.indexOf('function canonicalProjectTitle(value) {');const end=script.indexOf('async function registerProject({mixed',begin);
assert.ok(begin>0 && end>begin);
const calls=[],state={projectId:null};let shelf=[{name:' Tune Up ',path:'/owner/tuneup.zuckervid'}];
const api=async (route,body)=>{calls.push(route);if(route==='/wizard/projects')return {projects:shelf};if(route==='/wizard/projects/open')return {project_path:body.path};if(route==='/wizard/projects/new')return {ok:true};};
const scope=vm.createContext({state,api,String,Map});vm.runInContext(script.slice(begin,end)+'\nthis.choose=selectCanonicalVideoProject',scope);
(async()=>{assert.equal(await scope.choose('tune up'),'/owner/tuneup.zuckervid');assert.ok(!calls.includes('/wizard/projects/new'));console.log('ACTIVE_JM_CANONICAL_SELECTION_PASS');})().catch(e=>{console.error(e);process.exitCode=1});
