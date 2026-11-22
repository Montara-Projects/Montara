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

## JM-only deployment record — 22 Nov 2026, 01:03:19 UTC

The progress visibility fix was installed on LAB-JM only, not MAIN/FER. This does NOT accelerate the underlying engine and does not establish a speed improvement.

- Before deployment the latest five-video JM IngestStage record was failed after cancellation (POST /api/v1/wizard/cancel HTTP 200). At the deploy gate, zero JM files had been modified within five minutes, zero FFmpeg processes and recent worker writes were detected, and Mac Companion reported busy=false, version 0.6.14.
- Previous root-owned release /opt/montara/jmlab-issue346-20261122 remains intact. New release /opt/montara/jmlab-issue348-20261122 merged only PR #349 JavaScript onto the active JM version, preserving #346 360 and camera audio, recovery, logo, session and Mixer fixes.
- Active JS SHA256 292fcaff4c7be965a820d9afacaf7756a59a241fb9f9b8190246f8e0efe649b7. New versioned WSGI jmlab_issue348_wsgi.py preserves reviewed bridge, gateway and Stage route checks; browser-surface JS pin updated to exact new SHA. Both current and candidate WSGI passed Flask factory creation under real service UID montara-jmlab and the same actual service environment. Integrated JS progress-model and syntax tests passed.
- One-shot systemd rollout logged CHECKED_IDLE_AND_DIGESTS_PASS, DEPLOY_JM_348_PORTAL_SUCCESS, and UNAUTHENTICATED_HEALTH 403. Portal active from 01:03:19 UTC. JM and MAIN services and brokers remain active. Both HTTP unauthenticated health checks return 403. No new portal errors were observed.
- Rollback: remove only /etc/systemd/system/montara-h4-jmlab-portal.service.d/99-zz-jmlab-issue348-20261122.conf, systemctl daemon-reload, restart JM portal only to restore the unchanged #346 release. Protected manifest /var/lib/montara-maintenance/jmlab-issue348-20261122-deploy.json.
- Human E2E still pending: hard refresh JM, select corrected audio, retry Continue and confirm genuine IngestStage progress/elapsed time. Benchmark with FER #265 afterwards. Issue #348 stays open, PR draft, no claimed CPU/GPU or cache acceleration.
