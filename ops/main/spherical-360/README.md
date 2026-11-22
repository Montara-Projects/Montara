# MAIN spherical 360 panoramas and POV previews — 22 November 2026

## Result

The panoramic 360 UI, Add Point of View and framing/export code already
existed in MAIN. Its private Owner image routes did not. This is a
selective port of the human-approved JM #346 / #356 spherical image
routing, preserving MAIN's separate logo fix #389.

The change is active on MAIN private Owner portal port 8131, from
root-owned immutable overlay:
/opt/montara-main-release/main-approved-360-20261122

Parent release:
/opt/montara-main-release/main-approved-logo-20261122

Final portal-only systemd drop-in:
/etc/systemd/system/montara-h4-main-portal.service.d/zzzzzzzzzzzzzz-main-spherical-20261122.conf

Only three files changed relative to the logo-fixed parent:
- Owner browser bridge: private GET-only exact spherical-source-frame and
  spherical-preview routes, source under private Owner Uploads, limited
  media extensions and bounded parameters.
- Stage route contract: same JM-reviewed path and query validation.
- MAIN WSGI: new immutable overlay path and SHA256 pins.

The initial panorama uses authenticated fetch. Exact POV previews use
a CSRF-protected image fetch converted to a temporary browser blob URL.
Unregistered, cross-tenant, malformed or unsupported operations are
rejected. The Engine still verifies current-project source registration.

MAIN web/montara.js, original My Logo, Owner gateway, full-song
sessions, Mixer, Companion, CSS and render code are UNCHANGED.

## Evidence

- Rebuilt files match exactly the staged and activated candidate:
  bridge SHA256 44b6147a880e5069e2eae5750296d844acc2e0fa31c98b4bafb37db516675f1c
  Stage SHA256 9ba12d659621167420fbbbdc81c85d7597d06f751127628f87964863770787a8
  WSGI SHA256 432813519821f84c789763d7daf747ce52b0e9b9fea8250b59491b4a95cf6546
- Local Python Stage route contract 6 allowed / 16 denied PASS.
- Local Node browser bridge authenticated panorama and exact POV image
  regression, negative route cases, previous logo and editor flow PASS.
- On Linux VM WSGI import by the actual montara-release-main service
  account passed, as did Linux route smoke and JS syntax.
- After portal-only restart: public MAIN healthz HTTP 200;
  unauthenticated valid 360 panorama and POV URLs HTTP 401 (no longer 404);
  invalid parameters 404; previously working logo route remains 401.
  MAIN broker PID 84654 and Engine worker PID 90839 were unchanged.

No user media, saved project or underlying Engine was changed. Only MAIN
portal restarted (97978 to 98743); JM/FER were untouched.

## Reproduction

Use the checked-in immutable overlay builder on an authorized VM as root:

    python3 ops/main/spherical-360/build_overlay.py \
      --source /opt/montara-main-release/main-approved-logo-20261122 \
      --target /opt/montara-main-release/main-approved-360-20261122

Builder aborts if source hashes differ or destination exists. It never
modifies a live service. For scratch tests use --test-only on /tmp paths,
then run the included Python Stage and Node bridge tests against the
new output directory.

## Rollback and user acceptance

For rollback during a maintenance window, remove only the
zzzzzzzzzzzzzz-main-spherical-20261122.conf override, run
systemctl daemon-reload, and restart the MAIN portal only, after
verifying no in-flight requests. This returns to the prior
logo-fixed MAIN. Never restart the broker/Engine for this patch.

User must hard-refresh MAIN, enter Cameras with a registered 360 video,
verify panoramic frame, drag to rotate, add and name a POV, click to place,
and confirm exact preview. These UI results are not yet human-verified
on MAIN. No new full render is needed to validate that specific image fix.
Other heavy Stage issues and 503/409 remain under #356, #358, #386.
