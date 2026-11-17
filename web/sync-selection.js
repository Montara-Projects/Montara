/* Source roles and sync review policy. A confidence peak is not proof of sync. */
const SyncSelection = (() => {
  // Match Engine's YouTube _clip_master_ranges: a confirmed clip-local section
  // spans offset_sec + clip_start_sec through offset_sec + clip_end_sec.
  // The scalar offset is diagnostic only if valid override ranges exist.
  function cameraRanges(clip) {
    if (!clip) return [];
    const confirmed = Array.isArray(clip.offset_ranges) ? clip.offset_ranges.flatMap(item => {
      if (!item || !Number.isFinite(item.offset_sec) ||
          !Number.isFinite(item.clip_start_sec) || !Number.isFinite(item.clip_end_sec) ||
          item.clip_end_sec <= item.clip_start_sec) return [];
      const start = item.offset_sec + item.clip_start_sec;
      const end = item.offset_sec + item.clip_end_sec;
      return Number.isFinite(start) && Number.isFinite(end) ? [{start, end}] : [];
    }) : [];
    if (confirmed.length) return confirmed;
    if (!Number.isFinite(clip.offset_sec) || !Number.isFinite(clip.duration_sec) ||
        clip.duration_sec <= 0) return [];
    return [{start:clip.offset_sec, end:clip.offset_sec + clip.duration_sec}];
  }
  function eligible(clip) {
    return clip && !clip.no_audio && !clip.low_confidence &&
      !clip.unstable_sync && !clip.error;
  }
  function overlap(range, {start, end}) {
    return Math.min(range.end, end) - Math.max(range.start, start) > .5;
  }
  function review(files, clips, {start = 0, end = Infinity} = {}) {
    const result = {ready: [], silent: [], uncertain: []};
    for (const file of files) {
      if (file.usage === 'filler') continue;
      const clip = Object.values(clips || {}).find(c => [c.source_path, c.path].includes(file.path));
      if (clip?.no_audio) {result.silent.push(file); continue;}
      if (!eligible(clip) || !cameraRanges(clip).some(span => overlap({start, end}, span))) {
        result.uncertain.push(file);
      } else result.ready.push(file);
    }
    return result;
  }
  // The preflight prevents absolute noncoverage. It does NOT promise full
  // coverage, edit-plan validity or a successful export: Engine guards remain.
  function windowCoverage(files, clips, {start = 0, end = Infinity} = {}) {
    if (!Number.isFinite(start) || start < 0 ||
        !(Number.isFinite(end) || end === Infinity) || end <= start) {
      return {valid:false, covered:false, available:[]};
    }
    const available = [];
    for (const file of files) {
      if (file.usage === 'filler') continue;
      const clip = Object.values(clips || {}).find(c => [c.source_path, c.path].includes(file.path));
      if (!eligible(clip)) continue;
      available.push(...cameraRanges(clip));
    }
    return {valid:true, covered:available.some(span => overlap({start, end}, span)), available};
  }
  return {review, windowCoverage};
})();
