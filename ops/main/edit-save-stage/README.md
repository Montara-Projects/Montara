# MAIN Edit/Save Shot timeout fix — 23 November 2026

## Real evidence and defect

After visible Stage shots were restored in PR #394, the user confirmed
functional audio/video previews but reported Save Shot returning
"Could not save your change."

Actual MAIN Engine journal, 22 Nov 2026 UTC:
- 23:29:13 PATCH /api/v1/edit/shot HTTP 200 after 8.309 seconds.
- 23:29:18 PATCH /api/v1/edit/shot HTTP 409.
- 23:30:11 PATCH /api/v1/edit/shot HTTP 200 after 7.702 seconds.
- GET /api/v1/edit/shot/frame: 11.149 seconds, HTTP 200.
- Hover video previews sometimes take 23–38 seconds, HTTP 200.

Some changes were therefore accepted even though the private Owner
gateway could return 503 because its socket default is about 6 seconds.
The actual Engine 409 is distinct: could be a stale revision or busy
render. Without response JSON do not claim which. Never auto-repeat
a mutation or silently suppress a 409.

## Live MAIN-only patch

Root-owned immutable overlay:
  /opt/montara-main-release/main-edit-save-20261123

Source includes reviewed logo, 360, review timeout and 305 thumbnails:
  /opt/montara-main-release/main-reviewed-frames-20261123

Four files change only:
- Owner gateway: AFTER Owner/CSRF/worker generation verification, 95 s
  socket read timeout for exact PATCH /api/v1/edit/shot, exact
  GET /edit/shot?index, /edit/shot/frame?index&choice&revision and
  /edit/timeline?kind=music. Exact on-demand hover review/preview/N
  receives 75 s. Existing review GET 95 s stays unchanged.
- MAIN web JS: during an Edit dialog, pause Stage review polling.
  When there are over 100 shots, poll at 12 s, not 1.5 s.
  Video hover requires 700 ms dwell on long concerts.
- Static JS SHA pin and MAIN WSGI immutable source/hash pins updated.

No Engine, broker, project, media, 360 widget, logo, Mixer, Companion,
full session, private route allowlist, or render implementation changed.

## Verification

- Python timeout contract: 7 accepted, 13 rejected patterns, prior
  review timeout remains valid.
- JS UI test: poll pauses during Edit; 12s cadence for long concerts;
  mutation blocks another poll.
- Existing 305 shot browser/CSRF, 360, logo, Mixer, audio and lazy
  thumbnail tests PASS on this candidate.
- Linux actual MAIN service-user WSGI import / digest preflight PASS.
- Builder reproduces four exact deployed hashes, refuses modified
  input hashes or existing destinations and never activates services.
- MAIN public health 200. Unauthenticated POST Save 403 both before and
  after patch, GET Edit/thumbnail/logo 401. Authorization unchanged.
- Only portal restarted after zero active HTTP connections.
  Broker PID 84654 and Engine worker PID 90839 unchanged;
  MAIN portal PID 144525 after successful activation.
- A first activation auto-rolled back due expecting 401 on anonymous
  POST; baseline was verified as 403. A second deployment passed with
  the original security boundary intact.

## Rollback

MAIN-only final override:
  /etc/systemd/system/montara-h4-main-portal.service.d/zzzzzzzzzzzzzzzzzz-main-edit-save-20261123.conf

In a safe window with zero active requests, remove only that override,
systemctl daemon-reload, restart ONLY MAIN portal. Previous MAIN
thumbnail+review+360+logo fix remains. Do not kill broker, worker or FFmpeg.

Rebuild a new immutable directory with:
  python3 ops/main/edit-save-stage/build_overlay.py --source SOURCE --target NEW_TARGET

Test with:
  python3 ops/main/edit-save-stage/test_edit_wait_scope.py NEW_TARGET
  node ops/main/edit-save-stage/test_editor_polling.cjs NEW_TARGET/web/montara.js

## Human verification pending

Hard refresh MAIN and reopen the SAME saved project and shot, obtain
current revision, change zoom once, Save Shot once and reload to verify.
Do not rapidly retry a previously uncertain write: the Engine may have
accepted it. If there is a real 409, preserve the user's edit and inspect
the sanitized response category (busy vs stale revision).

Draft #361/Engine #78 are NOT deployed. #358, #359 and Colibri #386
retain broad edit performance and conflict handling. CI #372 remains
blocked by billing. This is NOT yet a human-verified Main Save E2E.
