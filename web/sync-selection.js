/* Source roles and sync review policy. A confidence peak is not proof of sync. */
const SyncSelection = (() => {
  function review(files, clips, {start = 0, end = Infinity} = {}) {
    const result = {ready: [], silent: [], uncertain: []};
    for (const file of files) {
      if (file.usage === 'filler') continue;
      const clip = Object.values(clips || {}).find(c => [c.source_path, c.path].includes(file.path));
      if (clip?.no_audio) {result.silent.push(file); continue;}
      const overlap = clip && Math.min(end, clip.offset_sec + clip.duration_sec) - Math.max(start, clip.offset_sec);
      if (!clip || clip.low_confidence || clip.unstable_sync || clip.error || !Number.isFinite(clip.offset_sec) || !(overlap > .5)) {
        result.uncertain.push(file);
      } else result.ready.push(file);
    }
    return result;
  }
  // Check the user-selected audio window, not just the entire synced master.
  function windowCoverage(files, clips, {start = 0, end = Infinity} = {}) {
    if (!Number.isFinite(start) || start < 0 ||
        !(Number.isFinite(end) || end === Infinity) || end <= start) {
      return {valid:false, covered:false, available:[]};
    }
    const covered = review(files, clips, {start, end}).ready.length > 0;
    const available = [];
    for (const file of files) {
      if (file.usage === 'filler') continue;
      const clip = Object.values(clips || {}).find(c => [c.source_path, c.path].includes(file.path));
      if (!clip || clip.no_audio || clip.low_confidence || clip.unstable_sync || clip.error ||
          !Number.isFinite(clip.offset_sec) || !Number.isFinite(clip.duration_sec) ||
          clip.duration_sec <= 0 || (Array.isArray(clip.offset_ranges) && clip.offset_ranges.length)) continue;
      available.push({start:clip.offset_sec, end:clip.offset_sec + clip.duration_sec});
    }
    return {valid:true, covered, available};
  }
  return {review, windowCoverage};
})();
