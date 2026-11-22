# MAIN: Preparing your shots review timeout, 23 November 2026

## Diagnosis

MAIN UI enters Preparing your shots then sends GET
/api/v1/wizard/review?render=1. The real MAIN Engine worker logged this
request on 2026-11-22 22:48:03 UTC, completing successfully with HTTP 200
after 7640.6 milliseconds. The Owner gateway's default socket timeout was
approximately 6 seconds, hence a false portal HTTP 503 was possible.

This precisely matches the previously verified JM failure #356. The
underlying render/Engine was NOT shown to have failed. At investigation,
MAIN had public HTTP 200, about 28 GiB RAM available, 25 GiB disk free,
no active FFmpeg process and no live portal HTTP request.

## MAIN-only fix, active

Immutable root-owned overlay:
  /opt/montara-main-release/main-review-timeout-20261123

Parent, which already contains MAIN logo and 360 fixes:
  /opt/montara-main-release/main-approved-360-20261122

Only gateway and MAIN WSGI overlay path/SHA pin changed. The private gateway
allows up to 95 seconds for exactly GET /api/v1/wizard/review with render=0
or render=1 and optional validated shot index (1-5 digits). It does this
only AFTER Owner authorization and worker-generation validation, on the
authenticated worker socket. Other timeouts, broker authentication,
Media, Mixer, 30-song sessions, Stage UI, logo, 360 views, exports,
Companion and original project files remain unchanged.

The builder at ops/main/review-timeout/build_overlay.py aborts on changed
approved source file hashes or an existing target. It creates code only:
no service restart, data migration, cache deletion or project modifications.
Two modified files reproduced byte-for-byte against deployed candidate.

## Tests and activation

- Local test_timeout_scope.py: 4 approved + 12 denied routing patterns PASS,
  including duplicate query keys, wrong method, malformed shot and other APIs.
- Linux VM Owner runtime WSGI import and SHA preflight PASS, 10 scope cases PASS.
- Only MAIN portal 8131 restarted, and only with zero active HTTP connections.
  MAIN broker PID 84654 and Engine job PID 90839 were unchanged.
- MAIN public health HTTP 200; anonymous private review route 401, logo
  route 401; unsupported 360 query 404.
- Portal new PID 141526, active with this overlay; other workers untouched.

Active systemd drop-in:
  /etc/systemd/system/montara-h4-main-portal.service.d/zzzzzzzzzzzzzzzz-main-review-20261123.conf

Rollback in a maintenance window: remove only this final drop-in, run
systemctl daemon-reload, restart ONLY MAIN portal after verifying no in-flight
requests. The previous release retains BOTH logo and 360 fixes.

The first activation SSH command failed before authentication (no remote
changes). A subsequent direct authenticated connection successfully activated
this reviewed patch with rollback-protected smoke tests.

## Human verification and limitations

User should hard-refresh MAIN, open the SAME existing project from Your
Projects, and check the Stage frames load. No reupload, duplicate project,
cache reset, job kill or extra MP4 render is required. Human authenticated
MAIN E2E is still pending.

This addresses one premature timeout, not generic slow thumbnail preparation,
>95-second Stage operations, 409 writes, 305-shot thumbnail routing or
Cloudflare proxy limits. Continue separately under #356, #358 and Colibri
#386. GitHub Actions billing #372 remains blocked.
