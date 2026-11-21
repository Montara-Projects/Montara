# MAIN / T4T QA fixture: temporary FER read-only terminal access

**Issue #332, owner JM, FER @luccifer00, created 21 November 2026.**

## Status — no media has been shared yet
VM montara-test (GCE montara-pruebas-10292226, europe-west3-a) has a new root-owned private folder:

    /srv/montara/qa-fixtures/t4t-reference-jam/

It is root:montara-qa-readonly, mode 0750. Linux users fer and jm are members of the dedicated read group; neither can write to the fixture. Real checks: read README as fer PASS; access MAIN private Owner workspace under /var/lib/private as fer DENIED PASS. No OAuth secrets, tokens, credentials, Cloudflare routes, files from users or real music have been copied. Source MAIN/JM/FER/Engine/Companion are untouched.

## FER instructions once authorized
Use existing SSH/IAM as OS user fer; do not request MAIN OAuth or privileged Owner roots.

    id
    ls -lah /srv/montara/qa-fixtures/t4t-reference-jam/
    find /srv/montara/qa-fixtures/t4t-reference-jam -maxdepth 2 -type f -printf '%P %s bytes\n'

Once files are published, verify them against a restricted signed/off-repo checksum manifest and run read-only ffprobe on exactly authorized files. Benchmark outputs and caches belong in a separate FER scratch workspace, not the fixture. Do not publish or distribute original concert media. Do not read from /var/lib/private owner dirs, change access controls or modify MAIN data.

## Publish contract — NOT YET IMPLEMENTED
Chema signs in to MAIN and chooses the exact T4T jam/project/recordings for FER QA. Confirm his authorization and any needed participant/media rights. An audited root-controlled publisher must:

1. Resolve exact authenticated Owner identity, project and selected assets; reject symlinks, path traversal, stale references, open writes and mismatched fingerprints.
2. Verify SHA256, bytes and time metadata and store a versioned manifest with Engine and Companion pins; no secrets or private media paths in GitHub.
3. Place only explicitly approved originals or compact derivatives in the private fixture, no mutable hardlinks unless reviewed and proven safe.
4. Capture reference and disposable test projects separately so nightly test cleanup never removes the fixture.
5. Confirm fer can read only the released assets, not other customers' MAIN/JM sessions, and cannot write into fixture.

VM has only ~11 GiB free after first cleanup; **DO NOT** upload 16x25GB videos or expand 16x4h WAV to VM. R2 is not enabled (#324). A capacity plan with R2 or authorized external originals must precede a huge fixture.

## Temporary, reversible access
FER access expires when benchmarks finish or after 30 days from fixture first publication, whichever occurs sooner. The operator records publication and expiry dates in the restricted manifest. Revoke fer group membership or set root-only folder permissions, verify denied access with a fresh fer session, and post evidence on #332. A user merely uninstalling the app never revokes Linux access; this is an explicit operations grant. The owner's retained fixture is independent from FER access and must be reviewed separately before deletion.

This PR is DOCUMENTATION ONLY. No actual T4T media shared. No MAIN/FER deployment or user deletion. Coordinate in #216, #321, #267 and #331.
