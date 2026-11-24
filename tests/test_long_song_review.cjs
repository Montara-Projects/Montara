/* Long Song UI guard and timestamp entry, no private media. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(__dirname+'/../web/full-session.js','utf8');
const start=source.indexOf('const LONG_SONG_REVIEW_SECONDS =');
const end=source.indexOf('function drawSessionSongs(songs)', start);
assert(start>0 && end>start);
const prompts=[];
let approved=false;
const context={
  clock:seconds=>Math.floor(seconds/60)+':'+String(Math.floor(seconds%60)).padStart(2,'0'),
  window:{confirm:msg=>{prompts.push(msg);return approved;}}
};
vm.createContext(context);
vm.runInContext(source.slice(start,end)+
 ';globalThis.parse=parseConcertSplitTime;globalThis.long=longSongsNeedingReview;globalThis.confirmLong=confirmLongSongReview;', context);
assert.equal(context.parse('9:20'),560);
assert.equal(context.parse('16:40'),1000);
assert.equal(context.parse('21:40'),1300);
assert.equal(context.parse('1:03:04'),3784);
assert.equal(context.parse('1000'),1000);
for (const bad of ['','9:67','-1','abc','1:2','1:70:01']) assert(Number.isNaN(context.parse(bad)));
const songs=[
  {name:'Song 01',start:0,end:64,selected:true},
  {name:'Song 02',start:64,end:1641.5,selected:true},
  {name:'Song 04',start:2083,end:2743.5,selected:true},
  {name:'Song 08',start:3235,end:3800.5,selected:true},
  {name:'Song 10',start:4007.5,end:4551.5,selected:true},
  {name:'Long unselected',start:4600,end:5700,selected:false},
];
assert.equal(context.long(songs).length,4);
assert.equal(context.confirmLong(songs),false);
assert.equal(prompts.length,1);
assert.match(prompts[0],/Song 02/);
assert.match(prompts[0],/Song 10/);
assert(!prompts[0].includes('Long unselected'));
approved=true;
assert.equal(context.confirmLong(songs),true);
assert.equal(context.confirmLong([songs[0]]),true);
assert.equal(prompts.length,2);
assert(source.includes('window.prompt('));
assert(source.includes('end: splitTime') && source.includes('start: splitTime'));
assert(source.includes('long_songs_reviewed: true'));
assert(source.indexOf('if (!confirmLongSongReview(songs)) return;') <
       source.indexOf("$('#sessionMix').hidden = true;",source.indexOf('async function renderFullSession')));
console.log('LONG_SONG_REVIEW_UI_PASS explicit_guard, four long segments, time entry');
