# MAIN #340 — Restore approved JM custom logo without replacing MAIN

## Status — 22 November 2026

**Activated selectively in MAIN portal 8131**, with a root-owned SHA-pinned
overlay at /opt/montara-main-release/main-approved-logo-20261122.
This is a port of the working JM logo upload/preview behavior, not a bulk
replacement. The base is the human-approved MAIN release from PR #382.
The backend bundle and Engine pins are unchanged.

The authenticated browser now uses:
- GET /montara/branding and POST /montara/branding;
- POST /montara/logo with multipart, Owner-CSRF and generation,
  9 MiB client limit and 10 MiB bounded gateway request;
- GET /montara/logo with optional numeric ?t for validated PNG/JPEG/WebP
  preview through a CSRF-protected blob URL.

The false synthetic branding response with has_logo=false was removed.
The widget enables Continue only when the upload succeeds and the saved
image can be fetched and decoded again. Errors produce a message and abort
after 45 seconds. The already authenticated Owner worker handles each route.
The original Engine image processing is unchanged.

Only the custom-logo UI region, Owner browser route allowlist, Stage route
contract, gateway upload bounds, static file hash and WSGI SHA pins change.
Full-song sessions, Mixer, Companion, Stage, private downloads and other
MAIN-specific features are preserved. No media touched.

## Deployment and rollback

The candidate passed preflight under the real montara-release-main service
account. Only montara-h4-main-portal.service was restarted, not its broker
or Engine. The first activation auto-rolled back because a loopback check
incorrectly expected HTTP 200. Local loopback requests return HTTP 403
without trusted HTTPS Host even when the service is healthy.

The corrected activation used the public Cloudflare URL and passed:
- MAIN public /healthz: HTTP 200.
- Private logo GET without auth: HTTP 401, not 404.
- Private branding GET without auth: HTTP 401.
- Bad logo query ?t=bogus: HTTP 404.
- Main Broker and Engine worker PIDs unchanged.
- Unit active; root-owned static SHA and WSGI preflight passed.

Rollback in a maintenance window: remove the sole drop-in
/etc/systemd/system/montara-h4-main-portal.service.d/zzzzzzzzzzzzz-main-logo-20261122.conf,
then systemctl daemon-reload and restart only the MAIN portal after checking
in-flight requests. Never stop a live broker or Engine for this patch.

## Reproduce

The source overlay is immutable and SHA-checked. Rebuild on the authorized
VM as root without executing a deployment:

    python3 ops/main/logo-340/build_overlay.py \
      --source /opt/montara-main-release/main-jm-approved-mixer-20a201d \
      --target /opt/montara-main-release/main-approved-logo-20261122

The builder refuses changed source digests or existing target and never
restarts services. To test source-to-output equivalence in scratch:

    python3 ops/main/logo-340/build_overlay.py \
      --source /tmp/reviewed-main-base --target /tmp/rebuilt-main-logo --test-only
    python3 ops/main/logo-340/test_stage_contract.py /tmp/rebuilt-main-logo
    node ops/main/logo-340/test_browser_bridge.cjs \
      /tmp/rebuilt-main-logo/urano/native_owner_browser_bridge.js
    node --check /tmp/rebuilt-main-logo/web/montara.js

All six patched files were rebuilt byte-for-byte from the pinned MAIN source
and matched the deployed candidate. Stage URL positives/negatives, the real
browser bridge (CSRF, multipart boundary, routes), and syntax checks pass.

## Human check still pending

Owner should hard-refresh MAIN, choose My logo, upload a real PNG/JPEG/WebP,
verify thumbnail and enabled Continue. Exported logo placement can be checked
on the next real user video; this patch has NOT uploaded real user media,
rendered a new MP4, or claimed authenticated-human E2E.

CI GitHub Actions billing issue #372 remains independent.
