# #392 — module pins and recovery rehearsal, 2026-11-23

**Scope:** checks against existing local JM-approved source and a disposable temporary directory; read-only against MAIN service. This is **not a disaster-recovery E2E of the live service**.

## Pin verification

- Existing checkout `Montara-MAIN-JM-Approved-Promotion-20261122` at `20a201d` (local `git rev-parse`).
- Git submodule references from `git submodule status`: Engine `9af275b18535005e36bd289a68ceb4a1d2f6c506`, Mixer `f15ff91c1b80fc5f157099dcd9451d958d553ae6`.
- A second existing local checkout (`Montara-main-t4t-qa-20261121`, `a79c862`) references the same pins.
- On the VM, the existing JM-approved bundle has an `engine` symlink to a directory named `engine-9af275b18535005e36bd289a68ceb4a1d2f6c506`; do not confuse a symlink target with the actual active Engine worker process.

**Open:** actual module paths and SHA-256 loaded in live Gunicorn preloaded process; actual Mixer import origin and SHA; active Engine process provenance. The ordinary SSH account cannot read `/proc/<pid>/environ` and final overlays are root-protected; subsequent remote inspection attempts ended with SSH connection closed. Do not retry around security controls or claim completion.

## Isolated recovery integrity rehearsal — PASS (limited)

From an already existing **local approved checkout**, a Python stdlib test used `tempfile.TemporaryDirectory` to:

1. Copy four **non-secret repository source files** into scratch `snapshot`, computing and retaining SHA-256 checksums.
2. Restore those four files into an independent scratch `reconstructed` tree, check hashes.
3. Introduce deliberate synthetic corruption of one scratch file and confirm SHA mismatch.
4. Roll back that file from the scratch snapshot and verify all hashes equal again.
5. Destroy temporary scratch at context exit.

Output:
```json
{"source":"JM approved local 20a201d snapshot","files_verified":4,"snapshot_hash_match":true,"isolated_restore_hash_match":true,"synthetic_corruption_rejected":true,"rollback_restored_exact_hashes":true,"scratch_deleted_on_exit":true}
```

**Interpretation:** checksum-based copy/corruption-detection/recovery logic works on four source files. This does **not** prove: production backup availability, durable SQLite restore, media/project recovery, WSGI imports, real root-only overlay reconstruction, restart/repin procedure, or authenticated E2E. No live service, persistent database, customer project, original media, cloud billing or Cloudflare configuration changed.

## What is needed to close both gates

- FER+JM approve privileged read-only **runtime file/module-origin audit**, capturing sanitized `PYTHONPATH`, active WSGI source hash, module provenance, Engine/Mixer actual process/inode/version; no secrets, no cross-owner data.
- Build production-equivalent immutable release candidate in an isolated test environment from the actual overlay sources; verify manifest file tree hashes and module imports.
- Perform a **test-only** restored Owner SQLite + representative anonymized media project, integrity checks, project reopen/edit and test render/Companion; prove rollback with no effect on MAIN/FER/JM jobs. Record versioned reproducible commands/results.
- Only after bilateral ACK and idle-window safety check should any production switching be considered.
