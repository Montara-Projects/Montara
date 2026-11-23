# LAB-JM Video Cuts — precise roll boundaries + enlarged Edit timeline

Date: 2026-11-23. Owner-approved specification: keep the existing Video Cuts
line above the frames, reuse **the same continuous cut boundary timeline**
in the Edit dialog, with horizontal zoom and scrolling. Do not duplicate
frame thumbnails, redesign 360 controls, change the master song clock or
change the underlying project without an explicit Save.

## Root cause reproduced by code inspection

The existing draggable handles called `showPatch('/edit/timeline', ...)`,
which sent a PATCH request. The LAB-JM browser route allowed **only**
`GET /api/v1/edit/timeline?kind=music`; its security bridge denied PATCH,
and the Cloudflare transport cannot forward arbitrary PATCH. The Owner
gateway and Stage allowlist also lacked a music cut write route. A browser
handle could therefore move locally but never save a new boundary.

## Minimal contract repair

- Explicit `PATCH /api/v1/edit/timeline` for the **music** kind on the private
  Stage allowlist; no generic write proxy.
- Browser turns just that PATCH into `POST /urano/v1/native/rpc/api/v1/edit/timeline/save`;
  authenticated Owner gateway restores the original PATCH to the Engine.
- Gateway validates exact JSON keys `kind, project_id, revision, index, at`,
  kind=music, bounded index, finite timestamp, and revision fingerprint.
  Existing Owner authorization, worker generation, CSRF and Engine's
  revision/range/clip coverage validation remain mandatory.
- Engine `server/edit_timeline.py` already has the atomic music roll:
  left duration grows/shrinks, right duration moves inversely, while
  programme/master clock stays fixed. The Engine is **unchanged**.
- The existing line handles visually resize both adjacent bars during drag,
  reverting on cancellation/error. Save only after pointer release.

## Edit dialog UX

- Under the camera/framing controls: **Video cuts** line from the same
  `makeCutTrack` renderer as the original overview. No frame images.
- Zoom control adjusts pixels per second. Continuous horizontal scroll
  navigates the full song (hundreds of cuts). It centres initially on the
  selected shot; zoom updates the track width without rebuilding hundreds
  of DOM nodes on slider changes.
- The `Original framing` control is **hidden only in this dialog**;
  cropping/framing algorithms and all 360 UI remain untouched.
- Saving one boundary updates the source timeline, refreshed overview,
  and zoomed line; stale revisions do not overwrite a newer edit.

## Isolation and version

- Source baseline: `/opt/montara/jmlab-stage359-on-audio379-candidate-20261123`
  on top of human-approved Audio #379.
- New, **not-yet-live** root-owned overlay:
  `/opt/montara/jmlab-cut-timeline-20261123-stage359-audio379`.
- No modifications to shared MAIN, LAB-FER, Engine, broker, Owner project,
  source/proxy media, Audio #379 implementation or 360 framing.
- Overlay WSGI/static hashes and integrity manifest updated;
  Audio `web/montara.js`, `web/full-session.js` and
  `urano/native_owner_mix_http.py` match the current Stage+Audio baseline.
- Existing LAB-JM Owner job is active, so **do not restart the portal** or
  repin systemd until the owner has closed the active editing session and
  idle can be confirmed. This PR is DRAFT; code-only validation does NOT
  imply a functional E2E pass or deployed feature.

## Checks and acceptance

- Isolated restricted-user WSGI preflight PASS on staging overlay.
- JavaScript `node --check` PASS.
- 11 regression checks for exact music timeline route / bridge / Owner
  validation / UI and 8 Audio project tests PASS (19 in total).
- Existing native browser bridge Node test PASS; Stage shot isolation
  5/5 PASS and Stage preview isolation 4/4 PASS.
- Full browser drag+save/reopen with user's 300+ cut song still pending.
- A prior unrelated macOS `test_native_owner_stage_snapshot.py` case
  fails due to `/private/var` vs `/var` path aliases; this is NOT
  evidence that the cut feature failed, and has not been concealed.

## Rollback

After verifying LAB-JM has no active editing job, do not disturb current
`zzz-jm-stage359-audio379-20261123.conf` or Audio #379 drop-in. If
candidate goes live, only a *new final* portal PYTHONPATH override should
be added, preserving the approved bundle. Revert by removing **only that
new override**, `daemon-reload` and restart **only** LAB-JM portal when
idle, then verify Audio #379 Save/Open, Stage Edit and 360.
