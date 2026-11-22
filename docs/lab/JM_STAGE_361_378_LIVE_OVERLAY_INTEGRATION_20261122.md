# LAB-JM: Controlled live-overlay merge of PRs #361 and #378

Date: Sunday, November 22, 2026.
**Status: isolated, hash-pinned candidate. Not deployed in live LAB-JM.**

## Verified original baseline

- Running portal: montara-h4-jmlab-portal.service, loopback port 8130.
- Its current reviewed WSGI overlay is /opt/montara/jmlab-mixer-label-hotfix-20261122.
- Underlying immutable JM bundle: SHA 61a57fd9ad46df4a8cfc0ae9c3b270b28119e009.
- Exactly that SHA is the GitHub base commit of PR #361, which enabled a genuine three-way merge instead of blindly replacing deployed assets.
- Active JM Engine is pinned to 9af275b18535005e36bd289a68ceb4a1d2f6c506, while Engine PR #78 references abd98667a1afbbf0e0de3c8e4ff4cacbd8ece7fe. These are DIFFERENT Engine builds.
- At the start of inspection, mixer_adapter and FFmpeg were running within a JM job. No Engine or portal restart performed.

## Integration performed

1. Retrieved code-only snapshots of the newest installed Owner overlay. No user projects, videos, credentials, session tokens or DB copied.
2. Per-file three-way merge: live deployed Owner code as ours, immutable JM bundle SHA 61a57fd as base, stacked PR #378 (including #361) as theirs. Only one merge conflict, in the 305-shot review counter.
3. Resolved the conflict by only refreshing global reviewShotCount on full review, never on one-shot partial:true responses. Retained lazy thumbnail loading, invalidation, ongoing mixer/session functions, review controls and uncertain Swap anti-replay protection from live JM.
4. Added the updated cut-editor.js to the explicit, SHA-256 pinned Owner static allowlist. This asset had previously been served unchanged from the original immutable bundle; PR #361 changes were not otherwise visible to the current portal.
5. Recomputed verified SHA-256 pins in native_owner_browser_surface.py and the isolated reviewable WSGI preflight, preserving the existing full-session.js and montara.css bytes.
6. Staged code-only copy in /opt/montara/jmlab-stage359-pr361-378-candidate-20261122. No systemd unit/drop-in was changed, no public port changed, no media/production data changed.

## Tests actually executed

- macOS Node/VM: 409 Save draft preservation, 305-shot partial refresh without dropping remaining 304, installed lazy thumbnail behavior, private Owner browser-bridge, 202 pending-to-ready private MP4 and terminal 202 rejection, Stage shot and preview isolation, updated SHA and module syntax checks PASS.
- VM isolated synthetic Flask Owner tests (real SQLite session/CSRF/workspace authority, mocked downstream transport): six cases PASS, including 409 Engine versus 409 Owner, 503 Engine versus 503 Owner, no Save replay and bad CSRF denial.
- VM synthetic authenticated Stage static route tests: all five assets were returned with HTTP 200 and byte-for-byte matched the staged files: montara.js, cut-editor.js, montara.css, owner-bridge.js and full-session.js. Unauthenticated access returned 401.
- Candidate WSGI module import and hash-pinned preflight PASS on the actual Linux VM.
- These tests do NOT constitute a real Cloudflare/Companion E2E on the user's 305-shot project.

## Human E2E gates with FER still pending

- [ ] Inspect the user's known completed concert export, verify actual decodable audio/video from the file. The user reported that this MP4 already exists locally. The file path and its bytes have not been inspected here.
- [ ] Review code with FER and cross-check #360 Windows/FER baseline, #361/Engine PR #78, #378 and the current LIVE JM overlay. Stage fixture and device versions must be equivalent before performance comparison.
- [ ] Engine #78 candidate must be reconciled with current JM 360/Mixer additions in a separate canary. Live Engine uses a different SHA and cannot be replaced indiscriminately while audio jobs run.
- [ ] Test same real project in an authenticated isolated LAB-JM browser: 305 shots, 360, short inserts, cold/warm hover, Edit, Save twice, stale 409 recovery, long Swap, complete render, Mac Companion export and playable MP4 with audio.
- [ ] Record browser-to-feedback timings and normalized Owner/broker/Engine stage durations; classify any real Cloudflare 503/409 independently of local mock tests.
- [ ] Investigate green video artifacts with permitted sample, ffprobe/camera projection data, not speculative GPU/codec fixes.
- [ ] Human JM and FER sign-off, safe downtime, rollback; no restart of running mixing/render jobs.
- [ ] GitHub Actions billing blocker #372 must be resolved and Linux CI completed.

Issue #359 remains P0 / In Progress. The integrated *candidate* passes local and VM synthetic safety checks; live deployed user-facing E2E and FER acceptance are not yet done.
