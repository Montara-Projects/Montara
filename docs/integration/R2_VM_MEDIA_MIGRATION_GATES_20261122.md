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

## Actualización: candidatos y protecciones comprobados el 22/11/2026

El inventario de una segunda pasada (solo lectura) separa los temporales en uso de posibles residuos históricos:

| Árbol | Tamaño | Última modificación / referencia | Decisión |
|---|---:|---|---|
| `/var/tmp/montara-jm-canary-abd98667-20261122` | 3.7 GB | 22/11, **3 descriptores abiertos** | **PROTEGER**, canary/QA JM activo |
| `/var/tmp/montara-caption-vocals.qvZ7ehjz` | 1.6 GB | 18/11, 0 descriptores abiertos en inspección | **Candidato**, verificar owner y referencias funcionales antes de borrar |
| `/var/tmp/montara-beta-segment2-diagnostic` | 100 MB | 18/11, 0 descriptores abiertos | **Candidato**, preservar evidencia QA |
| `/var/crash` | 651 MB | Crash dumps de 15 y 20/11 | **Candidato**, archivar trazas útiles antes de purga |
| `/home/fgardel00` | 9.7 GB | usuario que **ejecuta túnel Cloudflare activo**, múltiples QA/checkouts/backup antiguos | **NO eliminar en bloque**, coordinar FER/#334 |
| `/opt/montara/bundles` | 6.8 GB | Todas las carpetas listadas tienen al menos una referencia desde unidades `systemd` (algunas históricas) | No clasificar como huérfanas sin revisar cada servicio/deploy/rollback |

Adicionalmente, `/var/lib/private` ~18 GB incluye ~15 GB JM Owner **con un job activo** y ~1.7 GB MAIN Owner; `/home/fer` ~13 GB es propiedad funcional FER. No tocar. Raíz 96 GB / 68 GB usados / 29 GB libres.

**Criterio:** un recuento de FDs = 0 y una fecha antigua NO prueban ausencia de referencias DB, de un workflow o de reanudación futura. Todo queda protegido hasta copia verificada/permiso y ventana de mantenimiento; no se hizo borrado ni transferencia.

**Evidencia Stage del 22/11:** el usuario comunica MP4 E2E local correcto. La máquina conectada disponible es Mac; exploración de sus carpetas Montara/Exports y del Companion no encontró un **MP4 nuevo del 22/11**, aunque el Companion local da /health=200; el endpoint de vídeo sin sesión respondió 403. Si exportó Stage Windows, el archivo está en otra máquina no conectada y hay que verificarlo allí; no declarar validación binaria independiente de este archivo. La E2E humana previa en Stage Windows quedó verificada en #255 el 17/11.

**Estado:** auditoría solo lectura, sin limpieza automática ni alteración de la sesión JM actual.


## Approved owner routing to R2 and compute-only VM (2026-11-22)

The product owner requests moving all persistent VM user material to account-separated Cloudflare R2, leaving a lightweight computing host. The following product tenant labels are those already established for the pilot; the newly dictated names Gamets and Fed/Fernando are interpreted as Amehc and Fergardel respectively. Labels DO NOT authenticate a subject or grant access: reconcile Google/OAuth subject IDs and owner/project membership before live migration.

| Source VM owner or alias | Destination R2 tenant | Action |
| --- | --- | --- |
| JM / JMLAB (dictated Gamets) | **Amehc (pilot-amehc)** | Copy persistent original videos, photos, audio, exports and all referenced editing/project/session state; verify, cut over, then prune VM copies |
| FER / Fer / Gardel / Fergardel / Fed / Fernando / FERTRIAL | **Fergardel (pilot-fergardel)** | Same; enforce ownership isolation, verify restored projects and only then prune |
| MAIN / BETAMAIN | **T4T (pilot-t4t)** | First independently verify the user-reported backup at another location; avoid duplicate upload only if inventory/checksums and restore fully pass. Otherwise migrate to T4T before pruning |

Target VM: only application executables, essential operating/runtime infrastructure, narrowly scoped service identities, minimum operational databases/metadata if still needed locally, bounded temporary processing space and safety/observability logs. Human product accounts remain in the authenticated application; do not maintain redundant interactive Linux users. Do NOT delete necessary systemd isolation service principals based solely on their number. AI compute workers should share the same lifecycle/quotas with no permanent VM media library.

Migration classification must be semantic: large JSON project and session state and referenced blobs are user information even when their extensions are not mp4/jpg/wav. Git checkouts, Python libraries, cached render work, binaries and crash files are not automatically cloud media and require separate retention/pruning rules.

The user authorizes removing original VM copies **after** successful, independently verified R2 or other accepted cloud backup, correct tenant ownership, full-project restore and editorial/Companion E2E; do not erase the only good copy. Preflight: R2 EU authenticated read/write, three real 100 GB tenant quotas, object checksums, safe reference cutover, rollback. No migration or pruning has been completed simply by writing this specification.

Status correction: the formerly active JM service montara-h4-jmlab-job-07dfd1308025ec6aa2ff2e1de7e71cb6.service was stopped and verified inactive, PID 0, cgroup empty on 2026-11-22; its ledger entry was set to stopped. Earlier active-job notes are historical; do not treat them as current.
