/* Experimental FER B9: project Engine crop-local sync evidence onto a full master clock.
 * Pure policy; NOT wired into wizard/Stage and never a substitute for Engine verification.
 */
const HybridStageContract = (() => {
  'use strict';
  const version = 'fer-b9-stage-sync-v1';
  const finite = v => typeof v === 'number' && Number.isFinite(v);
  function fail(reason) { return {ok:false,reason,version}; }
  function validRange(r, clipDuration) {
    return r && finite(r.offset_sec) && finite(r.clip_start_sec) &&
      finite(r.clip_end_sec) && r.clip_start_sec >= 0 &&
      r.clip_end_sec > r.clip_start_sec && r.clip_end_sec <= clipDuration + .001;
  }
  function project({fullMasterDurationSec, cropStartSec, cropDurationSec, clips, threshold=6, fullMasterPath=null} = {}) {
    if (!finite(fullMasterDurationSec) || fullMasterDurationSec <= 0 ||
        !finite(cropStartSec) || cropStartSec < 0 ||
        !finite(cropDurationSec) || cropDurationSec <= 0 ||
        cropStartSec + cropDurationSec > fullMasterDurationSec + .001 ||
        !finite(threshold) || threshold <= 0)
      return fail('invalid_master_window');
    if (!clips || typeof clips !== 'object' || Array.isArray(clips) || !Object.keys(clips).length)
      return fail('missing_engine_clips');
    const output={};
    for (const [id, clip] of Object.entries(clips)) {
      if (!clip || typeof clip !== 'object' || !clip.source_path ||
          !finite(clip.offset_sec) || !finite(clip.duration_sec) || clip.duration_sec <= 0)
        return fail('invalid_clip_metadata');
      const verify=clip.verification;
      if (clip.no_audio || clip.error || clip.low_confidence || clip.unstable_sync ||
          !finite(clip.confidence) || clip.confidence < threshold ||
          !verify || verify.checked !== true || verify.unstable_sync !== false ||
          !Number.isInteger(verify.consensus_count) || verify.consensus_count < 2)
        return fail('unproven_engine_sync');
      if (clip.offset_ranges != null &&
          (!Array.isArray(clip.offset_ranges) ||
           !clip.offset_ranges.every(r => validRange(r,clip.duration_sec))))
        return fail('invalid_offset_ranges');
      const gOffset=cropStartSec+clip.offset_sec;
      const ranges=clip.offset_ranges?.length ? clip.offset_ranges.map(r => ({
        ...r, offset_sec:cropStartSec+r.offset_sec
      })) : null;
      const spans=ranges?.length ? ranges.map(r=>[r.offset_sec+r.clip_start_sec,r.offset_sec+r.clip_end_sec]) :
        [[gOffset,gOffset+clip.duration_sec]];
      if (!spans.every(([a,b])=>finite(a)&&finite(b)&&b>a) ||
          !spans.some(([a,b])=>Math.min(fullMasterDurationSec,b)>Math.max(0,a)+.5))
        return fail('no_global_master_coverage');
      // Confirm Engine's local result has actual overlap with the guide crop.
      // A good score from a clip completely outside the crop must never escape.
      if (!spans.some(([a,b])=>Math.min(cropStartSec+cropDurationSec,b) >
          Math.max(cropStartSec,a)+.5)) return fail('no_crop_overlap');
      output[id]={...clip,offset_sec:gOffset,
        ...(ranges ? {offset_ranges:ranges}:{}),
        hybrid_projection:{version,guide_start_sec:cropStartSec,guide_duration_sec:cropDurationSec}};
    }
    // Critical: a crop-local file cannot be passed off as a full master. The
    // Stage bridge remains disabled until the full timeline media contract exists.
    return {ok:true,version,projected_clips:output,
      master_duration_sec:fullMasterDurationSec,
      ready_for_stage:false,full_master_path:fullMasterPath,
      blocker:'Stage /wizard/prepare and Full Session still require a usable full master path and song timeline; pure projection is not an integration'};
  }
  return {project,version};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = HybridStageContract;