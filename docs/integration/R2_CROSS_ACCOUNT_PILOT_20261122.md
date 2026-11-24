# Montara R2 cross-account pilot — implementation and security runbook

**Date:** 2026-11-22. **Tracking:** #324, #325, #326, #327, #329. **Status:** preparatory documentation; NO production integration deployed.

## Verified Cloudflare topology

| Component | Cloudflare account | Value |
|---|---|---|
| Data/storage owner and billing | Personal account | `37db5e5f7ce32628852f0f5abef9fb66` |
| Application / Workers owner | Montara account | `f8e62d874245e8aadc01852ddf050f0c` |
| Active Workers (Montara) | Montara account | `montara-main`, `montara-lab-jm`, `montara-lab-fer` |
| Initial R2 bucket (personal account) | R2 | `montara-media-weur-pilot` |
| Bucket properties verified via Cloudflare API | R2 | location `WEUR`, `Standard`, jurisdiction `default` |
| Public bucket exposure | R2 | `r2.dev` disabled, no custom public domains |

**Important: a WEUR location hint is not the same as EU jurisdictional restriction.** The current bucket has `jurisdiction=default`. It MUST remain empty of real user material until the requested residency guarantee has been selected or an explicit alternative privacy decision is made. To guarantee EU jurisdiction, use Cloudflare R2 Dashboard → Create bucket → Specify jurisdiction → EU, then verify `jurisdiction=eu`; use e.g. `montara-media-eu-pilot`. Do not claim an existing default-jurisdiction bucket can be converted to EU. The default-jurisdiction pilot may be retained empty for testing or deleted only after confirming it contains no user data.

## Architecture: separate billing and compute accounts

1. Keep Cloudflare R2 billing and object storage in personal account `37db5e5f7ce32628852f0f5abef9fb66`; it is **not necessary** to activate a second R2 subscription in the Montara Workers account.
2. Cloudflare native R2 `env.BUCKET` bindings are **not** cross-account bindings. The Montara account accesses personal-account R2 through the **S3-compatible API** with AWS Signature Version 4; for EU-jurisdiction buckets the endpoint is `https://37db5e5f7ce32628852f0f5abef9fb66.eu.r2.cloudflarestorage.com`. The currently-created default-jurisdiction test bucket would use `https://37db5e5f7ce32628852f0f5abef9fb66.r2.cloudflarestorage.com` (not EU-guaranteed).
3. In **personal R2 account**, create an account-owned R2 API token with **Object Read & Write** limited to the **single chosen private bucket**. Do not use a global administrator token. Copy Access Key ID and Secret Access Key once. Do NOT put credentials into source, issue/PR, browser localStorage, logs or public response.
4. In **Montara Workers account**, store them as encrypted Worker secrets (names proposed: `MONTARA_R2_ACCESS_KEY_ID`, `MONTARA_R2_SECRET_ACCESS_KEY`). Other configuration: `MONTARA_R2_ENDPOINT`, `MONTARA_R2_BUCKET`, `MONTARA_R2_JURISDICTION=eu`, `MONTARA_R2_ENABLED=false` until verified. Prefer a distinct isolated upload-signing Worker/service, with authenticated same-origin route through existing portal and explicit owner authorization; do not modify the currently running editing Worker during E2E.
5. Signing service authenticates current Google/OAuth session and checks project membership, tenant quota, upload idempotency, object key and size; it produces a **short-lived presigned S3 URL or multipart Part URL**, never exposes S3 credentials. Direct browser/Companion upload to R2 avoids the GCE VM. All object keys are server-generated under `tenants/<tenant_id>/projects/<project_id>/assets/<asset_id>/originals/<filename-id>`, not an untrusted client-supplied path.
6. Configure private bucket CORS for **exact** authorized origins (approved Montara MAIN, LAB-JM and LAB-FER only), methods used for S3 PUT/part upload and GET as required, headers for multipart/checksum, short reasonable max-age. CORS is NOT authentication; signed URLs, per-tenant auth, CSRF and quota checks are required. No public `r2.dev` or custom hostname.
7. To validate: bucket read and location/jurisdiction via Cloudflare API, restricted token with negative access to any other bucket, unsigned upload denied, signed test upload/list/download/checksum, two-tenant negative tests, quota overshoot/concurrent reservations, multipart resume/abort, cross-origin denial, OAuth negative tests, and read path via S3 Range. Keep E2E Stage→Companion→MP4 independent until explicit authorization.

### Credentials gate actually observed

Connected Cloudflare API can manage R2 buckets but **cannot provision R2 S3 API tokens** with current connector scopes: `GET /accounts/{id}/tokens/permission_groups` returned HTTP 403, requiring `account-api-tokens.write`. No credentials were generated or put into Workers; thus cross-account read/write is **not yet connected**. User may provision the narrow bucket-scoped token in personal Cloudflare Dashboard, or reconnect the connector with necessary token-provisioning authorization. Do not claim the quota or upload has gone live.

## Pilot quota contract: 3 × 100 GB decimal

The product-level cap is **100,000,000,000 bytes per tenant**, across **all projects and all users uploading on behalf of that tenant**. Aggregate pilot logical allowance: **300,000,000,000 bytes** (not a physical R2 prepaid reservation). Display labels supplied by product owner: `Fergardel`, `Amehc`, `T4T`; these are **labels, not verified Google OAuth subject IDs**. See the adjacent disabled manifest. Never bind names directly to permission grants; reconcile each to its authenticated `owner_id` before enablement.

A single bucket holds all tenants. Mandatory backend SQL transactions:
- `tenant_quotas(tenant_id PK, limit_bytes, committed_bytes, reserved_bytes, revision)`.
- `upload_reservations(upload_id PK, tenant_id, project_id, expected_bytes, expires_at, state, idempotency_key)`.
- Before presign: in one serializable/write-lock transaction, require `committed + reserved + expected <= limit`; then reserve. Reject on conflicts and retry safely.
- After authenticated and checksum-verified R2 CompleteMultipartUpload or PUT, move reserved bytes to committed exactly once; reject/abort mismatched size or key.
- On aborted/expired unfinished uploads, reconcile R2 multipart state and release only after safe confirmation. Avoid duplicate billing, abandoned multipart parts and TOCTOU across simultaneous uploads.
- Deletes reduce committed bytes **only after** object absence and reference checks; never delete originals still referenced by other projects or renders. Reconcile against R2 object inventory; log non-sensitive audit trails.
- Contributors' uploads count against **project owner's tenant**, not guest. Three 100 GB grants do not mean three R2 buckets or three Cloudflare accounts.

### Cost envelope

R2 Standard rate USD 0.015 per GB-month: 100 GB stored for a full month = USD 1.50; three fully occupied = USD 4.50. Cloudflare account free tier of 10 GB-month, if applicable, offsets USD 0.15 total → about USD 4.35, plus billable Class A/B operations, any Workers/CPU, taxes. These are metered usage estimates, not reserved monthly subscription quantities.

## Operations and rollback

No production Worker, broker, login route, or active render should be restarted during the user's live E2E. Prepare a separate integration PR and validate through tests/isolated environment. To roll back access, first disable issuing fresh presigned URLs, then revoke only the bucket-scoped personal R2 API token after any in-flight uploads are handled. Do not delete objects or the bucket as a rollback.

References:
- https://developers.cloudflare.com/r2/api/
- https://developers.cloudflare.com/r2/api/tokens/
- https://developers.cloudflare.com/r2/objects/upload-objects/
- https://developers.cloudflare.com/r2/reference/data-location/
- https://developers.cloudflare.com/r2/pricing/


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
