/* FER B10. Experimental dual-clock session contract; no network, no production integration.
 * Distinguishes an acoustic analysis crop, the full global timeline, and bounded listening.
 */
const HybridSessionClock = (() => {
  'use strict';
  const finite = n => typeof n === 'number' && Number.isFinite(n);
  const sessionIdOk = value => typeof value === 'string' && /^[a-f0-9]{12}$/.test(value);
  const denied = reason => ({ok:false, reason, stage_ready:false});
  function timeline({sessionId, fullDurationSec, cropStartSec, cropDurationSec, fullGuideAvailable=false, mode='video'}={}) {
    if (mode !== 'video') return denied('audio_only_pipeline_unchanged');
    if (!sessionIdOk(sessionId)) return denied('invalid_session_identity');
    if (!finite(fullDurationSec) || fullDurationSec<=0 ||
        !finite(cropStartSec) || cropStartSec<0 ||
        !finite(cropDurationSec) || cropDurationSec<.5 ||
        cropStartSec + cropDurationSec > fullDurationSec + .001)
      return denied('invalid_timeline');
    if (typeof fullGuideAvailable !== 'boolean') return denied('invalid_guide_availability');
    const window={start_sec:cropStartSec,end_sec:cropStartSec+cropDurationSec};
    return {ok:true,version:'fer-b10-dual-clock-v1',
      session_identity:sessionId,global_duration_sec:fullDurationSec,
      sync_window:window,
      // Existing browser currently seeks in listen-all.webm, and existing
      // /wizard/prepare expects a real master. A short crop is NOT one.
      full_guide_available:fullGuideAvailable,
      stage_ready:false,
      stage_blocker:'Global master for /wizard/prepare and editor/export is not independently represented in the current product API'};
  }
  function rangeRequest(clock,start,end) {
    if (!clock?.ok || !finite(start) || !finite(end) || start<0 || end>clock.global_duration_sec ||
        end-start<.5 || end-start>3600) return denied('invalid_listening_range');
    // The existing endpoint accepts a range for listening; no new endpoint is invented.
    // This is a bounded request, not a full-session playable guide.
    return {ok:true,kind:'bounded_listening_only',
      url:'/montara/session/'+clock.session_identity+'/listen?start='+encodeURIComponent(start)+'&end='+encodeURIComponent(end),
      global_start_sec:start,global_end_sec:end,stage_master:false};
  }
  function prepareExcerpt(clock,projected,clips,excerpt) {
    if(!clock?.ok || !projected?.ok ||
       projected.master_duration_sec !== clock.global_duration_sec ||
       !clips || typeof clips!=='object' || !excerpt ||
       !finite(excerpt.start) || !finite(excerpt.end) ||
       excerpt.start<0 || excerpt.end>clock.global_duration_sec ||
       excerpt.end<=excerpt.start || excerpt.end-excerpt.start>3600)
      return denied('invalid_projected_excerpt');
    const list=Object.values(projected.projected_clips||{});
    if(!list.length || list.some(c=>c.low_confidence || c.unstable_sync || c.no_audio || c.error))
      return denied('unproven_camera');
    if(!Object.keys(projected.projected_clips).every(k=>clips[k]===projected.projected_clips[k]))
      return denied('mismatched_projection');
    // Source remains separate: the Engine used the short crop ONLY to determine
    // global camera offsets; the excerpt names a global interval.
    const listen=rangeRequest(clock,excerpt.start,excerpt.end);
    if(!listen.ok) return listen;
    return {ok:true,version:clock.version,session_identity:clock.session_identity,
      global_duration_sec:clock.global_duration_sec,
      sync_reference:clock.sync_window, excerpt_global:{start_sec:excerpt.start,end_sec:excerpt.end},
      listening:listen,
      engine_verified_clip_count:list.length,
      stage_ready:false,
      requires:['Server-authorized global timeline/master capability','Stage wizard support for externally verified global sync map','Correct original-range mixing and export contract'],
      reason:'This is an inspection-only plan. /wizard/prepare still expects full master and computes its own sync.'};
  }
  return {timeline,rangeRequest,prepareExcerpt};
})();
if(typeof module!=='undefined' && module.exports) module.exports=HybridSessionClock;