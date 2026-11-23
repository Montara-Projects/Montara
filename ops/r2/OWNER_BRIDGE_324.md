# R2 / #324 — private Owner bridge and Google quota binding (isolated contract)

Implemented as **draft code and tests**, not as a production HTTP endpoint or an enabled Cloudflare Worker. This branch is stacked on PR #391 and does not modify that branch's code or existing MAIN/JM/FER services.

## Verified existing Cloudflare state (read-only, 23 Nov 2026)

- D1 European-jurisdiction `montara-r2-pilot-quotas-eu` has three `pilot_tenants`: `fergardel` 100e9, `amehc` 100e9, `t4t` 100e9 bytes. All **pending_identity** with `oauth_issuer=NULL`, `oauth_subject=NULL`, used=reserved=0. No real grants.
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

## Owner decision correction (23 Nov)

All three private testers use the SAME Basic-equivalent pilot storage quota: **100 GB each, 300 GB maximum combined**, with **no customer subscription charges during beta**. Future public subscription tiers must not be applied to pilot tenants. Live D1 has been corrected and read back; the seed SQL and tests are aligned in parent PR #391. No bucket cloning or additional bucket is necessary.

## Owner quota view + S3 service adapter (23 Nov 2026)

- `urano/r2_pilot_status.py`: `owner_quota_status(db, verified_principal)` produces only plan/quota/used/reserved/available bytes. It never accepts a client-selected tenant and rejects unbound or inactive owners. **No public endpoint exists yet.** A D1 adapter is required (the current DB code uses SQLite).
- `urano/r2_private_s3.py`: injectable server-side `PrivateR2S3Storage` for byte-exact fixtures using standard S3 `put_object`/`get_object`/`delete_object`; key validation limits access to opaque per-tenant test keys and 1 MiB fixtures. `build_private_r2_s3_client` requires optional boto3 in the trusted backend and only server-held scoped credentials. There is no HTML/JS exposure of S3 keys and no public S3 endpoint. Cross-tenant authorization occurs before the adapter in `r2_owner_bridge`.
- `tests/test_r2_pilot_status_s3_324.py`: fake S3 backend, quota read isolation, missing-identity denial, per-owner 100 GB cap, private object read isolation, invalid key rejection.
- Local aggregate: `python3 -m unittest discover -s tests -p 'test_r2_*py' -q` (24 tests pass).

**No real integration/deploy claim:** Worker `montara-r2-eu-bridge-v2` is still deliberately disabled with HTTP 503. The real Google `sub` values have not been approved/bound in D1. The two buckets are `jurisdiction=default`, although the region is WEUR; verify strict EU jurisdiction before production originals. The private account has not been authorized for a new live S3 test from this code. The quota meter is currently a backend read-model **only**, not a displayed MAIN UI; final UI requires a session-scoped `/api/.../quota` endpoint in the approved release. For final live integration, adapt the D1 metadata operations with atomic updates, enable an authenticated cross-account service-to-service transport with FER/JM sign-off (#392), add short-lived multipart and proper reconciliation (#326), then test owner A cannot read owner B through the actual authenticated HTTP path. Do not send the real cloud secret to a client or logs.
