'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(process.argv[2],'utf8');
const start='function completeReviewGroups(items, groupSize=6) {';
const end='let framesRequest=null;';
const b=source.indexOf(start);
const e=source.indexOf(end,b);
assert.ok(b>=0 && e>b);
const context={};
vm.runInNewContext(source.slice(b,e)+';this.ready=completeReviewGroups;',context);
const f=context.ready;
const row=(i)=>({
  index:i,
  thumbnail:null,
  thumbnail_status:'missing',
  preview_ready:false,
  preview_error:false
});
const make=(n)=>Array.from({length:n},(_,i)=>row(i));
const done=(rows,i)=>Object.assign(rows[i],{
  thumbnail:'private-thumb-'+i,
  thumbnail_status:'ready',preview_ready:true
});
let arr=make(248);
assert.equal(f(arr),0);
for(let i=0;i<5;i++)done(arr,i);
assert.equal(f(arr),0,'Do not publish first 5 without all 6');
arr[5].thumbnail='thumb5'; arr[5].thumbnail_status='ready';
assert.equal(f(arr),6,'Thumbnail alone is sufficient to open Edit; no hover MP4 barrier');
arr[5].preview_error=true;
assert.equal(f(arr),6,'A failed hover preview cannot block framing edits');
for(let i=7;i<12;i++)done(arr,i);
assert.equal(f(arr),6,'Cannot publish partial next six');
done(arr,6);
assert.equal(f(arr),12);
done(arr,12);done(arr,13);
assert.equal(f(arr),12,'Next 6 hold');
arr[14].thumbnail_status='failed';
for(let i=15;i<18;i++)done(arr,i);
assert.equal(f(arr),18,'A terminal failed image should not stall all later shots');
for(let i=18;i<247;i++)done(arr,i);
assert.equal(f(arr),246,'Last incomplete group of two must wait');
done(arr,247);
assert.equal(f(arr),248,'Trailing partial group becomes visible when all settled');
assert.equal(f(make(0)),0);
let short=make(4);
for(let i=0;i<4;i++)done(short,i);
assert.equal(f(short),4,'Short projects not stuck behind six-card minimum');
assert.ok(source.includes('const ready=completeReviewGroups(all);'));
assert.ok(source.includes('const items=all.slice(0,ready);'));
assert.ok(source.includes('if(state.waitingFrames && (ready || !all.length))'));
assert.ok(source.includes('Preparing your first six shots'));
console.log('MAIN_6_EDITABLE_SHOTS_PASS 248, thumbnail-only edit, no hover MP4 barrier, 6-card batches, short projects, failed frame safe');
