# Persistent storage rule for NEW Montara work

Owner directive: 2026-11-22. Applies to LAB-JM, LAB-FER, MAIN (including legacy BETAMAIN) and future AI/lab workers.

## Source of truth

| Trusted server deployment | R2 tenant ID | Product name |
| --- | --- | --- |
| jmlab / montara-lab-jm | pilot-amehc | **Amehc** (JM) |
| fertrial / montara-lab-fer | pilot-fergardel | **Fergardel** (FER, Fed, Fernando, Gardel) |
| main / betamain / montara-main | pilot-t4t | **T4T** (MAIN) |

The user said "T4P" once while discussing MAIN; the existing tenant **T4T** remains authoritative, to avoid inventing a fourth tenant.

**Never trust a browser-supplied tenant, label, bucket, owner ID, object key, path or endpoint.** Derive tenant from the deployment's trusted identity AND independently authenticate the OAuth owner_id against a backend-managed owner-to-tenant table. Mismatch or missing entry is DENY, never a fallback to another account.

The server routing policy is in urano/r2_tenant_routing.py, tested by tests/test_r2_tenant_routing.py. Only server-generated asset/project UUIDs and approved object classes may enter R2 keys:

    tenants/<verified tenant>/projects/<server project UUID>/<approved asset class>/<server asset UUID>.<validated extension>

Private R2 bucket montara-media-eu-pilot, EU S3 endpoint:
    https://37db5e5f7ce32628852f0f5abef9fb66.eu.r2.cloudflarestorage.com

The policy rejects persistent local or VM storage as final mode **after cloud cutover**.

## Required wiring before production

1. Prove EU-jurisdiction storage with S3 list/put/get/range, no default-jurisdiction fallbacks. Never disclose R2 credentials to browsers.
2. Map the OAuth owner and project access to one immutable tenant identity using trusted DB state; unregistered labs/AI agents fail closed.
3. Enforce real 100 GB-per-tenant atomic quota reservations covering all projects/devices, multipart completion/retries and idempotency. Fail closed rather than writing permanent VM fallback files.
4. Wire rule to Stage New/Latest, Editor save, audio, 360, sessions, project-state JSON, AI outputs, uploads, Companion-upload results and exports. A user-requested final MP4 on the user's own Mac/Windows machine is not a VM archive.
5. Use time-limited signed direct R2 uploads, no permanent originals on VM. VM retains only bounded job-lease-scoped scratch with safe inactive retention/TTL.
6. Migrate legacy JM and FER originals and referenced state after size/SHA-256 and full restore tests, and MAIN to T4T only if existing cloud copy is incomplete.
7. Test negative cross-tenant access, expired signatures, race conditions on quota, multipart retries, bucket outage, all media/JSON read paths, Stage->Editor->Companion MP4, and no stranded VM originals.

## Status / blockers

**Staged only in draft PR #370:** pure-Python routing policy, negative tests and isolated CI. Not a live storage integration. S3 access, authenticated signing, server caller wiring, owner/OAuth mappings, durable quotas, full backup/restore and VM deletion are not yet verified. Do not enable this guard in production before those dependencies, because it would prevent current saves.

Related: #324, #325, #326, #329, #371.
