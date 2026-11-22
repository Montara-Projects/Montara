# Issue #348: measured IngestStage visibility, before speed optimization

Links: #265 (FER E2E benchmark), #146 (proxy size), #147 (Intel CPU/VideoToolbox), #342/#343 (360 and recovery).

## Confirmed root cause, 22 Nov 2026

The current Owner web/montara.js renderStatus uses only the global wizard progress (0–22 during ingest). It neither renders the Engine stage_progress/progress_updated_at nor contains a separate visible progress bar. The Engine already serializes those fields and per-video tasks from IngestStage. The Owner gateway forwards JSON unchanged.

This PR is restricted to the original Owner UI:
- Show a real HTML progress bar during IngestStage. Display stage_progress as a percentage only when the Engine has sent a numeric stage_progress AND numeric progress_updated_at. Never turn global wizard progress into an invented ingest percentage.
- Before the first report, show an honestly indeterminate bar. Cap a still-running ingest stage at 99%; avoid regressions from out-of-order reports, reset the phase if filtering unsynchronized cameras causes a new preparation.
- Display elapsed time, active Engine task, number of selected video inputs, counted completed proxy and prepared tasks, and a warning if the last update is more than 45 seconds old.
- Reuse the existing 1–2s status polling, no new timers, no new worker requests and no media reads. Existing error and cancel behavior remains.
- Add the visible element dynamically via web/montara.js so the pinned legacy HTML need not be replaced.

Local checks: JS syntax PASS, new Node model tests PASS for unknown metrics, real vs global percent, elapsed, counts, stale updates, 99% cap and stage reset. No authenticated browser E2E yet.

## Performance baseline not established

Read-only inspection of JM project metadata found six project records, with newer projects containing five videos and one ingest stage marked running, but no finalized ingest elapsed_seconds in that record. This does not establish actual CPU, GPU, disk, network or cache bottlenecks, nor an end-to-end measurement. One resource snapshot showed 31 GiB RAM with 28 GiB available and low instantaneous system load; do not extrapolate.

Use existing FER #265 measurement methodology: time monotonic phases from Continue to first usable edit; independently record local Companion fingerprint/conversion/upload and remote VM IngestStage/sync/analysis; cold vs warm cache, bytes, codec/resolution/fps/360, resource use, hashes and audiovisual quality. Perform A/A comparable real runs, then A/B changing just one reversible variable. #147 local 8.2 percent Intel encoding improvement is not a proved IngestStage gain.

## Deployment and acceptance gates

Do not replace current LAB-JM overlay wholesale; preserve #346, camera recovery, splitPlan, logo, sessions and Mixer fixes. A real JM rollout needs versioned root-owned overlay, exact reviewed SHA preflight, Linux tests, idle worker/import/render check, rollback, and authenticated human verification. MAIN and FER untouched.

This PR restores visibility only. Issue #348 remains open pending human E2E, real baseline, bottleneck diagnosis and a verified reversible performance experiment.
