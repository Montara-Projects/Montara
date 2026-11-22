'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(process.argv[2],'utf8');
const start='// A long concert can contain hundreds of shots. Fetch private JPEGs only\n';
const end='let framesRequest=null;';
assert.equal(source.split(start).length,2);
const block=start+source.split(start)[1].split(end)[0];
const observed=new Set();
let intersection=null,rootMargin=null;
class FakeIntersectionObserver {
  constructor(cb,opts){intersection=cb;rootMargin=opts.rootMargin;}
  observe(img){observed.add(img);}
  unobserve(img){observed.delete(img);}
}
const ctx={IntersectionObserver:FakeIntersectionObserver};
vm.runInNewContext(block+'\nthis.__observer = frameThumbObserver;',ctx,{filename:'montara-lazy-observer.js'});
const observer=ctx.__observer;
assert.ok(observer);
assert.equal(rootMargin,'250px 0px');
const imgs=Array.from({length:305},(_,i)=>({
  dataset:{reviewThumbnail:'/api/v1/wizard/review/thumbnail/assets-v2/shot-'+i+'.jpg'},
  src:''
}));
for(const img of imgs)observer.observe(img);
assert.equal(observed.size,305);
assert.equal(imgs.filter(img=>img.src).length,0,
  'No image is downloaded before cards intersect viewport');
const shown=imgs.slice(0,7);
intersection(shown.map(target=>({target,isIntersecting:true})));
assert.equal(imgs.filter(img=>img.src).length,7);
assert.equal(observed.size,298);
for(const img of shown){
  assert.equal(img.src,img.dataset.reviewThumbnail);
  assert.ok(!observed.has(img));
}
intersection([{target:imgs[8],isIntersecting:false}]);
assert.equal(imgs[8].src,'');
assert.ok(observed.has(imgs[8]));
console.log('MAIN_305_LAZY_VISIBLE_SHOTS_PASS 305 held, 7 viewport images loaded, nonvisible unchanged');
