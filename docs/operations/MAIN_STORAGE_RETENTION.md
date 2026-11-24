# MAIN storage retention and admission policy (proposal, non-destructive)

Status: **approved direction from owner, 2026-11-20; NOT activated in live MAIN**. The owner explicitly approved a conservative MAIN retention policy and safe JM cleanup. Staging236, FER, billing, running services, user originals and active sessions are outside this change.

## Invariants

1. Keep **all active project metadata, originals, sessions, outputs, saved mixes, and user-owned exports** until deliberate deletion/retention decision by that user. A download does not imply authorization to delete.
2. Scope by authenticated owner and project. No cross-owner traversal, cross-lab cleanup, cross-device actions, or symlink following; fail closed on ambiguous ownership, missing metadata, or unverified active jobs.
3. NEVER remove the original uploaded media, source files, user edits, persistent renders, credentials, backups or material needed for resumable uploads. If an upload may be resumable, retain it.
4. Main, JM, FER and Work quotas are separate; thresholds are **per volume**, never evidence that one user owns the capacity.
5. A cleanup candidate must be closed, explicitly classified as ephemeral/regenerable by the producer, have no live job/lease/lock/open descriptors or direct references, pass owner/path and age checks and have a recoverability proof. Unknown is `protected`.

## Proposed classes (not auto-deletion guarantees)

| Class | Initial retention | Additional gate |
|---|---|---|
| Active sessions/projects/originals | No automatic expiry | Explicit owner delete only |
| Finished MP3/MP4, saved mix, user export | Keep until explicit owner delete | Download alone not enough |
| Partial/resumable upload | 7 days *inactive* | Never if live/resumable/needed by session; user-specific recovery gate |
| Proxy/cache documented regenerable | 7 days after final job & no reference | Producer must prove regeneration |
| Render scratch | 48h after **completed** job, verified published output | Never while render/preview/retry is possible |
| Non-sensitive technical logs | 14 days rotation | Preserve diagnostics for incidents and audits |
| Backups | Separate restore/retention procedure | Never automatically remove from this policy |

## Capacity alerts and admission (proposed, not deployed)

- At **75%** disk used: alert to operators, record largest scoped owners and growth trend without paths containing secrets.
- At **85%**: require preflight storage reservation and avoid large jobs without confirmed headroom. Do not kill running jobs or block safe project retrieval.
- Every new render/upload: compute worst-case temporary bytes + committed bytes + reserve, with concurrent allocations counted; reject **new** work with a clear retry-later explanation only when reservation cannot be satisfied. Do not unilaterally set a low global GB cap incompatible with 4K/360 workloads.
- Reserve safety floor should be calibrated from measured render temp consumption, not guessed; until then alert-only for quota controls.
- Per-plan user quotas are a separate product decision; this policy does not choose price-tier quotas.
- No automatic cleanup until audit dry-run output has been reviewed by JM+FER and approved per shared-VM protocol, with restore/rollback tested.

## Read-only dry run

`python3 tools/maintenance/storage_audit.py --root /var/lib/private/MAIN_OWNER_DATA_ROOT --max-depth 4`

`storage_audit.py` **does not delete, change permissions, kill jobs, or follow symlinks**. It only summarizes file counts, sizes and classifications to stdout as JSON. An unknown file is always classified `protected`. An unprivileged scan that lacks access reports `scan_errors`; it is **not** evidence of an empty directory. Collect aggregate output only, not private paths/data, in project issues.

## Current 2026-11-20 baseline

Shared `/` 96 GiB total / 86 GiB used / 11 GiB available (89%). MAIN current scoped `Uploads` approximately 17.24 GiB; `Sessions` approximately 4.15 GiB; `Mixer` approximately 0.54 GiB. LAB-JM upload content ~6.0 GiB, with a worker active. Treat all as protected without further metadata authorization. Not a deletion approval. Staging236 nginx listeners remain configured and require separate authenticated E2E and rollback review before retirement.
