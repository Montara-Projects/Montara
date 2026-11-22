# VM-to-R2 media migration gates (read-only audit)

**Audit snapshot:** 2026-11-22 14:19 UTC, project `montara-pruebas-10292226`, shared VM `montara-test`. This file is a plan and an audit, **not** a deletion authorization.

## Current disk shape (observed, approximate)

| Scope | Used | Constraint |
|---|---:|---|
| Root filesystem | 68 GB of 96 GB; 29 GB available | shared GCP VM, other services run here |
| `/var/lib/private` | 18 GB | systemd private Owner runtime trees, **do not remove live** |
| private JM Owner tree | 15 GB | **one active JM render worker** during audit |
| private MAIN Owner tree | 1.7 GB | retained project/session, do not delete |
| `/home/fer` | 13 GB | FER-owned, no authorization to migrate/delete |
| `/opt/montara/bundles` | 6.8 GB | code/runtime bundles; cannot be treated as media |
| `/home/jm/montara-data` | 111 MB | not the dominant media consumer |
| `/home/jm/montara-backups` | 152 MB | backup/rollback; preserve |

**The VM cannot literally keep only processes:** it needs executable bundles, transient workspace, per-tenant state/SQLite, logs and bounded caches. The target is no **durable media originals** in GCE once safely migrated, not an empty disk.

## Non-destructive workflow

1. **Gate R2:** private EU-jurisdiction storage, S3 cross-account token in secrets, verified upload/list/range/download, tenant quotas enforced. No migration to the temporary `default`-jurisdiction bucket until residency decision is resolved.
2. **Inventory with ownership:** per-owner project/asset identity, hash (SHA-256), bytes, creation time, refcounts, source path, active job/FDs, whether already cloud-backed. No traversal into FER/shared scopes under JM-only authorization.
3. **Quiescence:** never move media used by live rendering, mixing, upload, previews, Companion transfers or session rehydration. Run in agreed maintenance window for each owner, with service health baseline.
4. **Copy, not move:** stream or multipart originals direct to owner R2 prefixes with resume/verification; maintain originals unchanged on VM. Verify R2 ETag semantics correctly for multipart (ETag is NOT guaranteed MD5); compare independent full-file SHA-256 checksums and size.
5. **Dual-read cutover:** update metadata refs transactionally only after cloud object verification, retain VM fallback and rollback; validate editor sync, 360 frame seeking, audio previews, offline Companion render and project re-open.
6. **Restore drills:** simulate browser/Companion disconnect, signed URL expiry, range retrier, R2 unavailability and full project restore without changing production assets.
7. **Retain then delete:** once validated and after explicit owner approval, apply bounded retention policy with two-pass manifest, backup and no open FDs. Delete **only scoped, verified, non-shared, inactive** originals, never roots, databases, project metadata, bundles or other owners' material. Confirm root filesystem space returned and health/E2E unaffected.
8. **Resource policy:** reserve adequate disk for download/range cache and temporary rendering, with limits and quotas; monitor `df`, inode pressure, upload errors and failed multipart cleanup.

## Ownership and hold points

- JM: can research JM files, but **15 GB private workspace active**; no deletion or migration cutover until render finishes and human MP4 confirmation.
- MAIN: retained 24-song reference session; needs independent backup/QA.
- FER: `/home/fer` and its runtime areas are not JM-owned. Separate FER approval required.
- Shared legacy Cloudflare Tunnel/betamain/multisong (#318/#334) is a different change and should not be coupled to media storage rollout.

**Expected benefit**: once proven, originals live in R2; VM retains bounded cache + runtime. **Unrealized today:** no bytes migrated; no VM deletions.
