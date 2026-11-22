# MAIN — Stage thumbnails invisible with 305 shots (#356)

## Root cause

The user confirmed that Stage cards now appear after MAIN #393, but
the picture in each card remains blank. MAIN's Owner bridge decorates
review JSON only for 200 or fewer shots. For 305 shots, it returns the
unmodified thumbnail URLs, which HTMLImageElement requests directly,
without Owner CSRF or the current Engine generation. Such private
URLs cannot load as anonymous images.

This is the same defect that JM #356 already fixed, with human
confirmation that 305 thumbnail photos did appear in JM. The main
Engine had returned HTTP 200 for the review itself. There was no
need to rerender, reingest, rebuild media or restart the worker.

## Live selective fix

Parent:
  /opt/montara-main-release/main-review-timeout-20261123

Active:
  /opt/montara-main-release/main-reviewed-frames-20261123

Only four code files differ from the previous MAIN release:
- Owner browser bridge intercepts exactly allowlisted private
  review/thumbnail image URLs, fetches with session CSRF and Engine
  generation and renders them as browser-local blob URLs. Other
  paths remain blocked.
- web/montara.js copies JM's 250px IntersectionObserver: cards
  fetch JPEGs only when approaching the viewport rather than
  requesting 305 images concurrently. A changed shot invalidates
  its previous image. Older browsers fall back to the authenticated
  eager image path.
- Owner browser surface pins the new web JS hash.
- MAIN WSGI root path and SHA pins updated.

No changes to the backend Engine, broker, Stage HTTP allowlist,
private gateway, 360, logo, Mixer, 30-song sessions, Companion,
downloads, CSS, project data or export.

## Tests actually passed

- Rebuild reproduced all four changed code files byte-for-byte.
- Node browser bridge synthetic 305-shot test confirmed the
  305-item JSON does not trigger 305 media downloads; one visible
  JPEG is fetched with authenticated Owner CSRF/generation as a
  browser-local blob, and disallowed paths/queries remain blocked.
- Existing bridge tests for logo, panoramic 360, private audio,
  saved projects and editor operations passed.
- A separate Node lazy-visibility test held 305 shots with zero
  initial JPEG requests, fetched only seven visible cards and left
  298 cards untouched.
- Linux actual MAIN service account WSGI SHA/import preflight
  and JS syntax checks passed.
- After portal-only restart public health 200, anonymous valid
  thumbnail 401, invalid thumbnail 404, prior logo/review 401.
  Main broker PID 84654 and Engine PID 90839 unchanged. Portal
  new PID 142343.

A first SSH file transfer was interrupted; that incomplete candidate
was NEVER activated. The final archive was independently checked
by SHA256 before installing; only the safe candidate was activated.

## Reproduce and roll back

Root-only builder: ops/main/long-review-thumbnails/build_overlay.py
It refuses source drift and existing output and never restarts a
service. Tests:
  node ops/main/long-review-thumbnails/test_browser_bridge.cjs TARGET/urano/native_owner_browser_bridge.js
  node ops/main/long-review-thumbnails/test_lazy_visibility.cjs TARGET/web/montara.js

Active systemd final override:
  /etc/systemd/system/montara-h4-main-portal.service.d/zzzzzzzzzzzzzzzzz-main-frames-20261123.conf

Rollback in a safe maintenance window: remove only this final
override, systemctl daemon-reload and restart MAIN portal ONLY after
checking no requests in flight. This restores review-timeout, logo
and 360 fixed MAIN. Never stop the broker or Engine for this fix.

## Human acceptance pending

In MAIN, hard refresh and reopen the SAME saved project from Your
Projects, with no new upload or rerender. Verify JPEGs appear as
Stage shot cards enter the viewport, and scrolling loads more.
No actual authenticated MAIN video-media visual verification has
yet been reported. Separate Stage timeouts, edit 409 and speed
issues remain under #356, #358 and Colibri #386. CI #372 is blocked.
