# Issue #379 — Audio-only project persistence, LAB-JM candidate

This pilot adds Owner-private audio project metadata without duplicating raw media. It is **not deployed** merely because the PR exists. Preserve active JM, FER and all MAIN releases.

## Scope

- `AudioProjects` under each verified Owner worker's persistent `ZUCKER_DATA_ROOT`, NOT a shared public directory or in-memory worker. Atomic, fsync'd file replaces guarded by an exclusive lock; opaque IDs, revisions and name-based upsert; no media deletion on project removal.
- Owner-routed endpoints `GET/POST /montara/mix/projects`, `GET /montara/mix/projects/<32hex>`, `POST /montara/mix/projects/<32hex>/delete`. Verify sources through the preexisting completed-upload resolver each time. Browser cannot select an Owner or storage path. Missing tracks fail explicitly with a recoverable 409.
- Your Projects divides Audio / Video; audio Open restores the same registered sources and saved manual faders/mutes/EQ/FX and track types, analyzing again as needed. Audio × requires confirmation and keeps originals and exports.
- The browser autosaves Owner's track controls, serialized by revision, and saves before/after final render; same case-insensitive title reuses a project slot.

## IMPORTANT current limitations

- Single-song Mixer audio-only mode only. Master-only and multi-song Session projects need their own persistence adapters, and are **not** claimed as done by this PR.
- No R2 backend. A project remains dependent on its Owner's original completed uploads within the persistent StateDirectory; no upload is repeated if those originals still exist.
- This cannot deduplicate historic video projects (#380), which use different Engine project IDs.
- No browser-authenticated E2E until deployed in idle JMLab, tested and approved by user.

## Deployment constraints

- Active JMLab serves a *different* `web/montara.js` from the Git baseline. `active_web_montara.js` is the reviewed, syntax-checked surgical merge on that exact currently active Owner overlay (SHA baseline `0ea9c8794591564565a716bb99a9791624fabf47093f05751aab9e3d2662680a`). Never replace the active portal with repo `web/montara.js` directly.
- On VM build new immutable JM `jm-<commit>` bundle from exact active pinned `jm-7ee6c58...`; update its manifest/pin. Build a new root-owned portal overlay by copying active `jmlab-mixer-label-hotfix-20261122` and replacing only the reviewed Owner bridge, strict private mix route and reviewed merged `web/montara.js`, updating SHA-256 pins in surface and WSGI. Preserve all other assets, authentication and the protected runtime environment.
- Use both auth/CSRF and owner-scoped broker for all new endpoints. Do not expose `/montara/mix/projects` on a public root without the Owner private gateway.
- Verify 100% backend/route/JS tests, WSGI preflight and runtime pin before *any* unit restart. Never restart while Owner uploads/renders/workers run. Keep rollback dropins; no deletion or migration.
- Acceptance: audio create → autosave → close Engine → reopen without reupload → edit fader/pan/FX → save, export → confirm no duplicate slot; video projects unaffected; owner B cannot see A's audio projects.
