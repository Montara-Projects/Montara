# MAIN runtime, VPC route and recovery verification — 2026-11-23

**Scope: read-only inspection. No rollout, no restart and no recovery action executed.** Supplement to `MAIN_LIVE_MANIFEST_2026-11-23.md` / #392.

## Actual service process and module resolution boundary

- `systemctl show montara-h4-main-portal`: `ActiveState=active`, `MainPID=149157` at inspection, `WorkingDirectory=/opt/montara/bundles/jm-61a57fd9ad46df4a8cfc0ae9c3b270b28119e009`.
- Effective `ExecStart` (not the unit's obsolete original command): `/opt/montara/jmlab-portal-runtime/bin/python -m gunicorn --preload --bind 127.0.0.1:8131 --workers 1 --threads 4 --timeout 600 main_project_name_wsgi:create_application()`. Verified separately against process command line (`ps`).
- The service unit has 27 applied drop-ins in order, ending with `zzzzzzzzzzzzzzzzzzzz-main-six-editable-20261123.conf` and referencing `/opt/montara-main-release/main-six-editable-20261123`. **The active entry point is `main_project_name_wsgi`, NOT a hypothetical six-shots WSGI.** The latest overlay has to be checked for its effective `PYTHONPATH` and its import precedence.
- The effective program *inside the Gunicorn process* cannot be attested simply by Git HEAD or directory names. The attempt to read `/proc/149157/environ` with the ordinary SSH user returned `PermissionError`. The root-owned final overlay is not readable with ordinary permissions. A later protected audit attempt did not complete, and no module import graph was emitted. **The exact file-level hash/import origin of every live Python module remains unverified**. Do not claim otherwise.
- A separate **read-only** inspection of the approved JM bundle showed that `engine` links to `/opt/montara/bundles/engine-9af275b18535005e36bd289a68ceb4a1d2f6c506/engine`, supporting the *bundle reference* to Engine `9af275b18535005e36bd289a68ceb4a1d2f6c506`. It does **not** prove that each current MAIN Engine worker loaded that exact version.
- Mixer pin recorded in #392 / product acceptance is `f15ff91` (GitHub history); **current resolved symlink and in-process hash were not independently confirmed**. `main@1887b0a6` is the latest Git HEAD observed, not the assembled runtime.

## Worker → private service → tunnel → portal

**Verified with live Cloudflare API reads against the account containing Montara Workers:**

1. `montara-main` Workers script settings contain VPC service binding `OWNER_PRIVATE_API` (type `vpc_service`, not R2).
2. The binding points to Connectivity Directory service `montara-main-private-8131`, `type=http`, `http_port=8131`, `host.ipv4=127.0.0.1`.
3. The directory service's `host.network.tunnel_id` matches the tunnel returned by the Cloudflare list named `montara-owner-fg`. The tunnel reports `healthy`.
4. The VM service is bound to loopback port `8131`, and the main portal is active.

This proves configured routing and tunnel identity, **not** a full authenticated browser E2E, per-user authorization, or successful video render. No secret keys, tunnel tokens or OAuth identity values were retrieved.

## Recovery / rollback procedure — DRY RUN ONLY; NOT EXECUTED

1. **Freeze and identify:** record the current `main` SHA and approved baseline, full ordered drop-in hash list from the companion manifest, exact overlay file tree hashes and imported module paths, Engine/Mixer pins, app identity, and private tunnel/VPC routing. Confirm live jobs and edit/save operations are quiescent; coordinate FER+JM ACK under #392.
2. **Backups:** ensure the Owner SQLite state and all referenced project/media backups are actually readable and restorable, including revision and file integrity verification; never infer safety from file presence. Preserve the current private owner state and original media. Do not expose secrets in the manifest.
3. **Build immutable replacement in LAB:** reconstruct the approved functionality into a SHA-pinned artifact from Git and explicit overlay sources; compare exact file hashes, import precedence, user isolation, authorization, 30-song/Mixer/360/editor paths. Keep both old and candidate artifacts, **no in-place edits**.
4. **Differential QA:** perform appropriate read-only/static checks and isolated smoke tests; verify Stage six editable JPGs, 360 coverage (#396), Edit/Save revision handling, preview, audio FX/pan/delay, saved projects, Companion macOS/Windows, private access and rollback. Full human/Windows acceptance only where behavior changes. CI #372 currently cannot run, so independently report test evidence rather than asserting green CI.
5. **Promotion gate:** only with explicit two-party approval and a verified idle window, take a documented restore point and switch the minimum required isolated portal component. No changes to shared broker/Engine/VM/Cloudflare by assumption; after switch verify health *and authenticated E2E*. Restore the old immutable release only on explicit abort/rollback gate, after verifying active jobs and DB consistency.
6. **Rollback to last validated live overlay:** restoration must use the prior known `ExecStart`, exact ordered drop-ins/`PYTHONPATH`, hashes, private VPC routing, saved DB state and a previously proven recovery procedure. Merely changing the Git branch or doing `git reset` is **not** sufficient. Never restart or repin blindly when other owner jobs may be active. Document elapsed time and success criteria from a nonproduction rehearsal before production use.

## Outstanding evidence

- Immutable file tree and all module import hashes in final root-owned overlay, backed by a privilege-controlled **read-only** runtime audit.
- Current active MAIN Engine worker SHA and Mixer import/version; provenance from #382 and final overlay.
- Real authenticated end-to-end network path and origin/authorization behavior.
- Actual backup/checksum/restore rehearsal and exact tested service repin procedure; none was run during this audit.
- FER sign-off on this evidence, then jointly approved consolidation/rollback plan in #392.

**Current classification:** routing configuration = independently verified; portal entrypoint = independently verified; Engine symlink in approved JM bundle = verified; in-memory module graph/Mixer pin = **unverified**; rollback = **procedure specified, not tested**.
