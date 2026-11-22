const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const source=fs.readFileSync(require('node:path').resolve(__dirname,'../web/track-types.js'),'utf8');
const context=vm.createContext({document:{addEventListener(){}}});
vm.runInContext(source+'\nthis.api=TrackTypes;',context);
assert.equal(context.api.sourceLabel('/private/Mary Vocal.wav'),'Mary Vocal');
assert.equal(context.api.label('Mary Vocal.wav'),'Lead vocal');
assert.equal(context.api.sourceLabel('Kick.wav'),'Kick');
console.log('TRACK_TYPES_SOURCE_LABEL_PASS');
