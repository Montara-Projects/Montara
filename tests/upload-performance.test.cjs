'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
for (const name of ['companion.js', 'resumable-upload.js']) {
  test(name + ' parses', () => {
    const source = fs.readFileSync(path.join(__dirname,'..','web',name),'utf8');
    assert.doesNotThrow(() => new vm.Script(source));
  });
  test(name + ' records phase durations without source filenames', () => {
    const source = fs.readFileSync(path.join(__dirname,'..','web',name),'utf8');
    assert(source.includes("'[Montara upload timing]'"));
    assert(source.includes('total_sec'));
    assert(!source.includes('filename: file.name'));
  });
}

test('a dropped response body retries only the ready proxy read', async () => {
  const source = fs.readFileSync(path.join(__dirname, '..', 'web', 'companion.js'), 'utf8');
  let reads = 0;
  const context = vm.createContext({
    AbortController, Blob, TypeError, setTimeout: resolve => resolve(),
    fetch: async url => {
      assert.match(url, /\/proxies\/ready\/file$/);
      reads++;
      return {ok: true, headers: new Headers({'Content-Length':'3'}), blob: async () => {
        if (reads === 1) throw new TypeError('Failed to fetch');
        return new Blob(['mp4']);
      }};
    },
  });
  vm.runInContext(source.replace('  async function fingerprint', '  globalThis.readProxy = readProxy;\n  async function fingerprint'), context);
  const received = await context.readProxy('ready', () => false);
  assert.equal(received.blob.size, 3);
  assert.equal(received.retries, 1);
  assert.equal(reads, 2);
  assert.equal(await context.readProxy('ready', () => true), null);
  assert.equal(reads, 2);
});

test('finish retries a transient 503 with the same upload identity', async () => {
  const source = fs.readFileSync(path.join(__dirname,'..','web','resumable-upload.js'),'utf8');
  const calls = [];
  const ctx = vm.createContext({
    setTimeout: resolve => resolve(),
    fetch: async (url, options) => {
      calls.push([url, options.method]);
      return calls.length === 1 ? new Response('{}', {status:503})
        : new Response('{"master":[{"path":"ready.wav"}]}');
    },
  });
  vm.runInContext(source,ctx);
  let retries=0;
  const result = await ctx.finishResumableUpload('same', () => {}, undefined, () => { retries++; });
  assert.equal(result.master[0].path,'ready.wav');
  assert.equal(retries,1);
  assert.deepEqual(calls,Array(2).fill(['/montara/uploads/same/finish','POST']));
});
