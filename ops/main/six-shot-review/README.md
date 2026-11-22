# MAIN — Six editable Stage shots and 360 source coverage audit

23 November 2026 (Europe/Berlin). Code-only release is already active.

Final immutable overlay: /opt/montara-main-release/main-six-editable-20261123
Approved source: /opt/montara-main-release/main-edit-save-20261123

Only web/montara.js, its static SHA and MAIN WSGI pins changed.
No changes to Engine, worker, broker, data, original uploads, 360,
logo, previews, Mixer, Companion or Export. Only MAIN portal restarted
at zero established HTTP requests. Engine PID 90839, broker PID 84654
unchanged; final MAIN portal PID 149157. Health 200, Owner routes
401 without session. Rollback is remove only the last MAIN systemd
drop-in (zzzzzzzzzzzzzzzzzzzz-main-six-editable-20261123.conf) and
restart MAIN portal only during a safe maintenance window.

Six-shot readiness:
- Show the first six cards only when thumbnails are ready. The next
  group of six appears only when that group is settled.
- Allow failed thumbnails as settled so Edit can repair them, and
  allow a final partial group or 1–5-shot project.
- Do NOT wait for optional hover MP4 previews before showing Edit.
  An exported or reopened project may never prefetch them, and
  waiting would leave Stage permanently blank.
- The Engine already processes photos/previews in three-shot groups
  in one background worker. This frontend fix does NOT claim to
  improve actual backend latency or change Engine scheduling.
- The first six show preparation progress; remaining groups show
  a count of shots ready to edit. Extra thumbnails remain lazy-loaded.

Tests: synthetic 248-shot, 305-shot authenticated JPEG/Owner bridge,
Edit polling pause, 360, logo, Mixer, short projects, partial group
and invalid preview status all passed. Rebuild with the root-only,
digest-pinned code-only build_overlay.py, which refuses existing targets.

Read-only 360 diagnosis on the newest modified MAIN project (248 shots):
- Registered spherical video: 728.88 seconds (12m 8.88s), 0.355 GiB
  confirmed by ffprobe. Registered flat video: 1155.16 seconds
  (19m 15.16s), 0.195 GiB; both files physically present.
- Synchronization offset of 360: +411.7827 seconds (6m 51.78s),
  confidence 64.57, not flagged low-confidence or unstable.
  First selected 360 shot at master 417.13s (6m 57.13s);
  102 shots use the spherical source.
- Other camera offset +228.6005s (3m 48.60s), confidence 74.75.
  Current Stage coverage starts at master +228.60s despite an
  originally requested start of 0.
- Exactly 2 inputs registered; no other video uploads in that
  same Owner Uploads root. This does not rule out an original
  longer 360 file on the user's computer or external storage.
- Do NOT change the validated offset or project footage implicitly.
  Find and verify an earlier/full 360 source and import only
  with explicit authority and safe project backup. A short input
  does not become longer by modifying the UI or render code.
- No render launched or media rewritten in this investigation.

Outstanding: HUMAN check that six thumbnails appear and Edit opens;
verify earlier/full 360 recording before export. Engine priority
thumbnails before expensive hover MP4 requires separate reviewed
backend work. PR #361 and Engine #78 remain DRAFT; do not deploy
those changes implicitly. CI #372 remains blocked.
