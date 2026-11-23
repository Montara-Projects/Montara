# R2 / #324 — private Owner bridge and Google quota binding (isolated contract)

Implemented as **draft code and tests**, not as a production HTTP endpoint or an enabled Cloudflare Worker. This branch is stacked on PR #391 and does not modify that branch's code or existing MAIN/JM/FER services.

## Verified existing Cloudflare state (read-only, 23 Nov 2026)

- D1 European-jurisdiction `montara-r2-pilot-quotas-eu` has three `pilot_tenants`: `fergardel` 100e9, `amehc` 250e9, `t4t` 500e9 bytes. All **pending_identity** with `oauth_issuer=NULL`, `oauth_subject=NULL`, used=reserved=0. No real grants.
- `montara-r2-eu-bridge-v2` contains two S3 secrets (names and types checked, **not values**). Actual Worker source is only `fetch() -> HTTP 503`, no S3/Google OAuth/tenant routing implementation. `montara-r2-bridge-pilot` has no bindings. MAIN/JM/FER Workers currently have only the private Owner VPC binding.
- Existing R2 buckets are WEUR/Standard **jurisdiction=default**, not confirmed strict EU. A bucket name with "eu" does not establish data residency; do not connect real owners or move their content until jurisdiction EU is resolved and verified.

## Candidate backend contract

`urano/r2_owner_bridge.py` provides:

- `verified_google_principal(identity)` accepts only the `GoogleIdentity` type from the server's verified Google ID token flow. **It does not itself verify JWT cryptography**. Upstream MUST verify trusted JWKS, issuer/audience, expiry, one-time nonce and PKCE and MUST NOT create `GoogleIdentity` from browser JSON.
- `bind_approved_google_owner(db, identity, tenant_key, approved_subject_by_tenant=...)` demands an explicit privileged, *private* operator map from tenant to verified Google subject, constant-time subject equality. No binding by email, display label, project name or arbitrary browser-supplied `sub`. The map is deliberately empty until three authenticated account sessions have been independently checked. Activation in the real D1 database has NOT happened.
- `upload_synthetic()` accepts <=1 MiB synthetic data and operates only with a currently active principal: reserve quota -> create unpredictable object key under server-derived tenant prefix -> put -> get -> SHA-256 + size readback -> register private asset metadata -> commit quota. On exception, remove the test object and cancel reservation where possible. This is **NOT** a production 25 GB multipart API; such an API requires a S3 adapter and content integrity verification.
- `read_private_asset()` selects the storage key only from `(verified tenant, asset_id, state=ready)` metadata, then checks SHA-256 and length. Never use a path supplied by a client, and never reveal raw bucket paths to browsers.
- Storage backend is a Protocol, replaced with in-memory FakePrivateR2 in tests. **No Cloudflare R2 request/credential has been exercised by these bridge tests**; the synthetic test proves policy logic, not production network isolation.

## Tests and gates

`python3 -m unittest discover -s tests -p 'test_r2_*py'` — 19 passing isolated tests total, 8 new tests for verified-Google binding, 3-tenant synthetic upload/readback, denied cross-tenant reads, wrong issuer, login absent, wrong object path, corruption rollback, idempotent asset IDs. No live customer data.

Before enabling real bridge:

1. Capture subject and issuer for Fergardel, Amehc and T4T **from each independent, verified server-side Google login**, and secure operator approval of tenant association. Do not publish subjects in GitHub and do not infer mapping from environment, labels or emails.
2. Implement D1-backed transactions preserving existing #391 quota correctness and create an authenticated private service-to-service endpoint that resolves Owner identity from server session (no public R2 secrets). Harden audit, replay, expiry, CSRF, HMAC/idempotency, rate limit, and cross-tenant read/write/delete denial.
3. Verify an S3-compatible client with **bucket-scoped secrets** against a truly EU-jurisdictional bucket. Run a *real* tiny synthetic object PUT→HEAD→GET-range→SHA-256→DELETE, including denied second tenant, without migrating originals; rollback every object.
4. Agree FER/JM release gate #392 before activating or connecting MAIN/FER/JM. Preserve existing buckets, VM and user media.
