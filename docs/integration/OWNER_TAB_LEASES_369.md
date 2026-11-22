# #369: multi-tab Owner Engine lifecycle — broker-side safety gate

Date: 2026-11-22. Stacked on #305 / PR #375, **not** an automatic-stop deployment.

## Why this is necessary

PR #272 adds a browser-triggered close after Companion reports a playable
local MP4 and checks only the Engine generation. Two active browser tabs can
share the same Owner/generation. Closing from one tab can still interrupt the
other. A pagehide/sendBeacon event is unreliable and insufficient proof that
native render, Stage, Mixer or Companion has finished.

## Implemented, tested contract

- An opaque 192-bit tab lease is created by the **root broker** after
  independently verifying the Owner's session/CSRF, canonical private project
  UUID and running Engine generation. The authenticated session is bound by
  SHA-256; raw session/CSRF tokens are not persisted in the lease DB.
- Leases, heartbeats, explicit release and in-flight RPC records share the
  **same SQLite database** as JobRecoveryLedger, permitting atomic
  BEGIN IMMEDIATE decisions that serialize with generation transitions.
- 90 seconds heartbeat TTL plus 120 seconds grace (configurable only on server)
  before an abruptly disconnected tab ceases to count as active. Browser
  pagehide cannot directly cause a stop. An expired tab cannot renew and must
  reauthenticate/obtain a new lease. A tab release is idempotent and does not
  stop Engine.
- Every active RPC has a server-owned in-flight operation record; an operation
  remains fenced even if its tab expires or is released. It is not auto-cleared
  after an arbitrary TTL, because upload/render tasks may outlive the tab.
- Per-Owner scope for each tab, session, project and generation. Unknown
  labels, malformed tokens, foreign sessions, stale generations and
  concurrent owner changes fail closed.
- The privileged stop reservation checks *in the same SQLite transaction*:
  exact running job + at least one registered tab for that generation + no
  remaining active or grace-period tabs + zero in-flight operations + a
  **trusted server-side** completion and idle attestation proving local MP4
  verified and no native, Companion or Mixer/export tasks.
- Only after all conditions pass does it atomically transition the exact job
  from running to stopping. Actual shutdown MUST still go through existing
  RestrictedTargetControl.stop_verified + independently checked cgroup empty
  + JobRecoveryLedger.confirm_stopped. A browser-supplied videoStatus=ready
  or generic Boolean does not count as this proof. The broker IPC includes NO
  operation to inject an idle attestation or request a privileged stop.
- If any source is uncertain, leave the worker running and report "busy".
  Preserve the completed local MP4 even when Engine remains active.

## Files in this PR

- urano/owner_tab_lease_guard.py — durable per-tab lease/RPC model, idle
  attestation, atomic stop-reservation gate; no systemd calls or timers.
- urano/owner_tab_lease_admission.py — strict independently authenticated
  Owner/project/CSRF broker IPC schema.
- urano/private_broker_service.py — authorized root-side tab operations
  (open/heartbeat/leave/RPC begin/RPC finish). No public HTTP endpoint or
  automatic service stop is added in this PR.
- tests/test_owner_tab_lease_guard_369.py and
  tests/test_owner_tab_lease_admission_369.py — same-Owner multi-tab, 2
  independent Owners, session-bound tokens, concurrency, RPC, reconnect,
  expiry/grace, crash/restart, stale generation, forged proof, idempotence.

## Important integration gates (NOT YET COMPLETE)

- [ ] Resolve shared-session CSRF rotation: SessionStore.rotate_csrf()
  currently replaces a single session-level token when another tab refreshes;
  this can invalidate the first tab. Design bounded per-tab CSRF proofs, or an
  equivalent server-authenticated multi-tab strategy. Do not weaken root
  Owner/CSRF validation or let clients choose owners.
- [ ] Expose a reviewed same-origin /tab/open, /tab/heartbeat, /tab/leave
  API from the Owner app with an explicit deployment flag; initialize a
  separate lease in each tab only *after* successful /native/ensure.
- [ ] Require the tab lease before all native RPC paths. The web bridge must
  broker-register an in-flight operation before granting or using any worker
  FD, and finish it in a robust server-side finally block. Protect rotated
  CSRF during long RPC completion; reject missing lease in the enabled
  generation instead of allowing legacy bypass.
- [ ] Enroll a worker generation into mandatory lease protocol when it
  starts. Existing workers and previously opened tabs MUST NOT be treated as
  fully instrumented simply because one new tab later registers. Until a
  generation is fully enrolled and all editor/companion paths covered, the
  old legacy worker stays protected from automatic stop.
- [ ] Establish a **real authenticated local Companion/server attestation**
  that MP4 is playable and no external render/export is active. The browser's
  /videoStatus=ready response is not an independent broker proof.
- [ ] Integrate with #272 verified local-MP4 release and #271 abrupt
  disconnect reconciliation, with an explicit behind-flag idle reaper.
  It must never rely on pagehide/sendBeacon alone.
- [ ] Cross-process race E2E under actual broker, real systemd and cgroups
  with two synthetic Owners/tabs + long RPC. Confirm next project does not
  raise BusyOwner after *legitimate verified* closure.
- [ ] JM and FER review, Windows/Mac playback/Companion checks, CI (#372),
  rollout and rollback. Never restart active JM/FER/MAIN worker during
  testing or enable auto-stop in production until gates are signed off.

## Status

**Server-side safety foundation complete with local isolated tests.
Full #369 functionality remains In Progress.** This change does not
close tabs, stop Engines, release VM memory, activate timers, change the
Chema editor UX, deploy services or touch user media. PR #272 stays
DRAFT/conflicting and MUST NOT merge merely because these broker-side
guards exist. Depends on PR #375 for constructor/startup non-interference.
