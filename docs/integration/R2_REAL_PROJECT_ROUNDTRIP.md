# R2 EU full-project recovery gate — executable implementation

Scope: isolated, operator-only integration. Implementation: urano/r2_workspace_archive.py. Server operator service: urano/r2_operator_roundtrip.py. Compatibility command: tools/r2_verify_project_roundtrip.py. Tests: tests/test_r2_workspace_archive.py.

## Actual read/write adapter

Boto3R2Store uses the exact EU endpoint:
  https://37db5e5f7ce32628852f0f5abef9fb66.eu.r2.cloudflarestorage.com

and private bucket montara-media-eu-pilot with SigV4 and managed multipart upload. It accepts credentials only from a trusted runtime; no secret values exist in this PR.

The full-workspace backup uploads Projects, Uploads, Sessions, WizardUploads, Mixer, Branding, Inbox, PushPacks and config.json to tenant-scoped immutable R2 snapshot keys:
  tenants/<verified-tenant>/snapshots/<snapshot-uuid>/files/<native-relative-path>

Every S3 object is independently read back and SHA-256 verified; source files are rechecked after the final upload. The manifest is written LAST as commit marker. A pinned manifest SHA-256 receipt is required for restoring. Restoration downloads into a NEW private temporary workspace and validates bytes, digest and timestamps. Montara's native JSON absolute paths are rewritten only in disposable local processing scratch, never in R2 originals. It opens restored native project files with the existing core.project.load_project function and checks that all master/songs/video inputs come from restored scratch rather than the VM originals. No deletion.

The operator CLI exits successfully with PASS_FULL_R2_EU_ROUNDTRIP and private proof JSON (0600) only when the full test passes.

## Secure invocation when credentials and authenticated ownership are available

- Trusted OAuth owner ID -> tenant mapping is a private server-owned JSON file with mode 0600, NOT user/browser data.
- Authenticated runtime injects MONTARA_STORAGE_EU_V2_KEY_ID and MONTARA_STORAGE_EU_V2_SECRET, stored already as secrets on the isolated Cloudflare Worker. Do not print values, put them in command-line arguments or commit them.
- Run from isolated Python environment with optional boto3 dependency installed and native engine on PYTHONPATH.
- Supply only a verified owner ID, trusted server instance identifier, source workspace, independent NEW restore scratch destination and NEW private proof output. The tool does not delete originals.
- Check actual EU token permission, because mere presence of encrypted Worker secrets does not prove EU R2 bucket access.

Illustrative argument shape (not executable without trusted identities and runtime credentials):

    python -m urano.r2_operator_roundtrip \
      --trusted-instance jmlab \
      --verified-owner-id "<verified-server-subject-id>" \
      --owner-registry "/private/admin/owner-to-tenant.json" \
      --source-root "/private/owner-data" \
      --restore-to "/private/scratch/a-new-restore" \
      --proof-json "/private/audit/new-r2-proof.json"

## Required gate before production and VM removal

1. Produce private SHA-256 source inventory.
2. Upload to verified EU S3 with correct tenant credentials/quota reservations and independently verify every remote object's bytes/hash.
3. Restore the full project to separate scratch from pinned manifest, then open each native edit with verified source media without using any VM original.
4. Test real browser Stage/Editor, 360 seeking, audio previews and Companion MP4 with R2-backed workspace.
5. Wire OAuth-authenticated read/write routes and atomic 100 GB tenant quota reservations (#324 #325 #326 #329).
6. Only then switch active owner read paths to verified R2, retain rollback, and clean safely scoped VM originals after active jobs end (#371).

## Implementation status (accurate)

The automated tests use an in-memory S3 test double, NOT live Cloudflare. They exercise backup -> SHA-256 -> restore -> native project open with original source made unavailable, and corruption/cross-tenant negatives.

The Boto3R2Store is a real S3 adapter, but a live authenticated connection to the user's EU bucket has NOT been demonstrated; the isolated Cloudflare Worker stores two encrypted secrets but is still disabled and not service-bound to production Montara. Actual save/open browser routes and 100 GB quota enforcement are NOT yet wired or enabled, so no production cloud backup proof or deletion is claimed. GitHub Actions billing/spending-limit failure is unrelated.
