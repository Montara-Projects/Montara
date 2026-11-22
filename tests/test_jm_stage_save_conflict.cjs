'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const text=fs.readFileSync(path.join(root,'web/montara.js'),'utf8');
const helper=text.slice(text.indexOf('async function showPatch('),text.indexOf('async function openShowReview('));
assert(helper.startsWith('async function showPatch('),'showPatch helper missing');
const calls=[];
let responseStatus=409;
let body={error:{message:'The edit changed. Reopen this shot.',code:'stale_edit'}};
const sandbox={
  fetch:async (url,opts)=>{
    calls.push([url,opts]);
    return {ok:responseStatus===200,status:responseStatus,json:async()=>body};
  },
  Event: class Event {constructor(type){this.type=type;}},
  document: {dispatchEvent: event=>calls.push(['dispatch',event.type])}
};
vm.runInNewContext(helper+'\nglobalThis.testShowPatch = showPatch;',sandbox);
(async()=>{
  let error;
  try{await sandbox.testShowPatch('/edit/shot',{revision:'revision-1'});}
  catch(e){error=e;}
  assert(error,'409 should reject');
  assert.equal(error.status,409);
  assert.equal(error.code,'stale_edit');
  assert.equal(error.message,'The edit changed. Reopen this shot.');
  assert.equal(calls.length,1,'No automatic replay or success event');
  assert.equal(calls[0][1].method,'PATCH');
  assert.equal(calls[0][0],'/api/v1/edit/shot');
  responseStatus=409;
  body={error:{message:'Wait for the current render to finish.'}};
  try{await sandbox.testShowPatch('/edit/shot',{revision:'revision-2'});}
  catch(e){error=e;}
  assert.equal(error.status,409);
  assert.match(error.message,/render/);
  assert.equal(calls.length,2);
  responseStatus=200;
  body={revision:'revision-3'};
  const result=await sandbox.testShowPatch('/edit/shot',{revision:'revision-2'});
  assert.equal(result.revision,'revision-3');
  assert.equal(calls.at(-1)[1],'montara:edit-saved');

  const cut=fs.readFileSync(path.join(root,'web/cut-editor.js'),'utf8');
  const fn=cut.slice(cut.indexOf('function musicShotDraft('),cut.indexOf('async function openMusicShot('));
  assert(fn.startsWith('function musicShotDraft('));
  vm.runInNewContext(fn+'\nglobalThis.testDraft=musicShotDraft;',sandbox);
  const attrs={
    camera:{value:'1'},
    yaw:{value:'38'},pitch:{value:'-7'},fov:{value:'89'},
    movement:{checked:false},playback_speed:{value:'1.25'},
    markMusician:{checked:true},rememberMusician:{value:'piano'}
  };
  const doc={choices:[{source_path:'/private/foo',label:'Camera 1',spherical:false},
    {source_path:'/private/bar',label:'Pianist',spherical:true}]};
  const draft=sandbox.testDraft(doc,key=>attrs[key],{get:()=>({zoom:1.2,x:0.4,y:0.5})},'Piano');
  assert.equal(draft.source_path,'/private/bar');
  assert.equal(draft.camera_label,'Pianist');
  assert.equal(draft.yaw,'38');
  assert.equal(draft.movement,false);
  assert.equal(draft.selected_view_name,'Piano');
  assert.equal(draft.flat_framing.zoom,1.2);
  assert(cut.includes('Reload latest shot, keep my choices'));
  assert(cut.includes('return openMusicShot(index,draft,latest)'),'Must use refreshed doc once');
  assert(cut.includes('saveAction.disabled=true'),'When camera missing, fail closed');
  assert(cut.includes("save.textContent='Saving…'"),'Immediate feedback');
  // A scoped server response must update ONE card, never delete 304 others.
  const ui=fs.readFileSync(path.join(root,'web/montara.js'),'utf8');
  const updateSource=ui.slice(ui.indexOf('async function updateFrames('),
                              ui.indexOf('async function swap('));
  assert(updateSource.startsWith('async function updateFrames('));
  const shot={index:158,thumbnail:'/new-shot.jpg',preview:'/api/v1/wizard/review/preview/158',
    duration_sec:2.5,camera_type:'fixed',candidate_count:4,thumbnail_status:'ready',preview_ready:true};
  const image={src:'/old-shot.jpg',hidden:false,dataset:{reviewThumbnail:'/old-shot.jpg'},getAttribute:()=>'/old-shot.jpg'};
  const summary={textContent:'Fixed'};
  const length={textContent:'2.0 s'};
  const button={disabled:false};
  const status={textContent:'',hidden:true};
  const thumb={dataset:{preview:'/api/v1/wizard/review/preview/158'},querySelector:()=>status};
  const fig={dataset:{index:'158'},classList:{toggle(){}},
    querySelector:sel=>({'img':image,'.thumb':thumb,'.src':summary,'.dur':length,'.swap':button})[sel]};
  const untouched={dataset:{index:'159'},removed:false,remove(){this.removed=true;}};
  const grid={children:[fig,untouched],querySelector:sel=>sel.includes('158')?fig:null};
  const hint={textContent:'305 shots'};
  const view={work:{generation:1},state:{platform:'youtube',framesPending:true,
    waitingFrames:false},swapping:new Set(),api:async()=>({items:[shot],partial:true,platform:'youtube'}),
    viewpointName:()=>null,stopFrameHover:()=>{},resetFrameVideo:()=>{},
    clearTimeout:()=>{},frameHover:null,frameThumbObserver:{observe(img){img.src=img.dataset.reviewThumbnail;}},toast:()=>{},fail:()=>{},
    $:sel=>({'#frameGrid':grid,'#framesHint':hint})[sel]};
  vm.runInNewContext(updateSource+'\nglobalThis.testUpdateFrames=updateFrames;',view);
  await view.testUpdateFrames(true,158);
  assert.equal(grid.children.length,2);
  assert.equal(untouched.removed,false);
  assert.equal(image.src,'/new-shot.jpg');
  assert.equal(length.textContent,'2.5 s');
  assert.equal(hint.textContent,'305 shots');
  assert.equal(view.state.framesPending,true,'partial update cannot clear global pending status');
  console.log('JM_STAGE_SAVE_CONFLICT_PASS (409 and 305-shot partial DOM)');

})().catch(e=>{console.error(e);process.exitCode=1;});
