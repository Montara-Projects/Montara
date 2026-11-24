'use strict';
// QA client helper, explicitly per track. The caller obtains fresh short-lived
// grants for each attempt; payload_json/jobId NEVER change across retries.
// No file bytes, names, paths, hashes, or grant contents go to logs.
const RETRYABLE_CODES = new Set(['AUDIO_TEMPORARY_TIMEOUT','AUDIO_TEMPORARY_IO']);
const MAX_ATTEMPTS = 3;

function pause(ms, signal) {
  return new Promise((resolve,reject) => {
    if (signal?.aborted) return reject(Object.assign(new Error('Cancelled'),{name:'AbortError'}));
    const timer = setTimeout(() => {signal?.removeEventListener('abort',abort);resolve();},ms);
    function abort() {clearTimeout(timer);signal.removeEventListener('abort',abort);reject(Object.assign(new Error('Cancelled'),{name:'AbortError'}));}
    signal?.addEventListener('abort',abort,{once:true});
  });
}
async function retryAudioTrack({jobId,payloadJson,grant,send,signal,onState=()=>{},sleep=pause}) {
  if (!/^[a-f0-9]{32}$/.test(jobId) || typeof payloadJson !== 'string' ||
      typeof grant !== 'function' || typeof send !== 'function') throw new TypeError('Invalid QA audio track request');
  for (let attempt=1;attempt<=MAX_ATTEMPTS;attempt++) {
    if (signal?.aborted) throw Object.assign(new Error('Cancelled'),{name:'AbortError'});
    onState({status:'preparing',attempt});
    // A new grant permits one retry of the SAME verified job and source payload.
    const freshGrant=await grant({jobId,signal});
    const response=await send({jobId,payloadJson,grant:freshGrant,signal});
    if (response.ok) {onState({status:'ready',attempt});return response;}
    const detail=await response.json().catch(()=>({}));
    const retryable=detail?.retryable===true && RETRYABLE_CODES.has(detail?.code) &&
      [422,429,503,504].includes(response.status);
    if (!retryable || attempt===MAX_ATTEMPTS) {
      onState({status:'failed',attempt,code:typeof detail?.code==='string'?detail.code:'AUDIO_FAILED'});
      const error=new Error('This audio track could not be prepared; other tracks remain available.');
      error.status=response.status;error.code=typeof detail?.code==='string'?detail.code:'AUDIO_FAILED';
      throw error;
    }
    onState({status:'retrying',attempt,code:detail.code});
    await sleep(attempt*400,signal);
  }
}
module.exports={retryAudioTrack,RETRYABLE_CODES,MAX_ATTEMPTS};
