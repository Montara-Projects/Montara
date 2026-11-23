# MAIN live service baseline — 2026-11-23 (read-only)

Tracking: issue #392. **Inventory only, NOT approval to deploy, re-pin or change anything.**

## Scope and evidence

- Captured from the authorized Mac via read-only SSH to the existing Montara VM; source is `systemctl show montara-h4-main-portal` and SHA-256 of actual unit/drop-in bytes. No contents of environment files, secrets, Owner records or media were copied.
- Service active at inspection, portal listens on `127.0.0.1:8131` via `main_project_name_wsgi:create_application()` (Gunicorn). Recorded PID at inspection: 149157; **ephemeral, not a version identifier**.
- GitHub default branch HEAD observed: `1887b0a6f0fea5f863be50d6039b17f60353f959` (#387). This is **not** the verified live runtime SHA.
- Approved JM bundle referenced by latest config: `20a201d257f8c720d3c3c608b050b18cdcae5636` (#382); Engine MAIN reported `9af275b` in #392 (not independently fingerprinted in this inventory).
- The last active listed overlay is `main-six-editable-20261123` (PR #397), layered after the #395 Edit/Save, #394 thumbnails, #393 review timeouts, #390 spherical views and #389 logo overlays. The PR descriptions label these **LIVE OVERLAY**, not merged release artifacts.
- Unit has **27 drop-ins** plus one base service file. Their ordering is the order returned by systemd, not evidence that earlier overlays remain effective if superseded later.

## Unit and ordered drop-ins (hash of file bytes)

| Order | Unit/drop-in | SHA-256 | Referenced release/overlay directory |
|---:|---|---|---|
| 0 | `montara-h4-main-portal.service` | `202f9d9bce1f93aba875469274af39185e7e9ec77c63aaf6d4316600947568ba` | base unit |
| 1 | `20-main-private-session-20261120.conf` | `d638ad2d18ad159c8d20fd96ceeb1d72793ca69b75226437b7502414801ce5cd` | `/opt/montara-main-release/main-session-overlay-20261120` |
| 2 | `30-main-account-menu-20261120.conf` | `af6e2cbbffa4dd62e8dbbd32fe465164a9377e07641e441797825d7940cf941d` | `/opt/montara-main-release/main-account-overlay-20261120` |
| 3 | `40-main-boundaries-20261120.conf` | `3608f5716697d12a56527fe8f7993667f481afa32894aadabdcf85c5a4e653a3` | `/opt/montara-main-release/main-boundary-overlay-20261120` |
| 4 | `50-main-auto-song-transitions-20261120.conf` | `923bcb0e404579ac2e031b3271fb2a20362b9618acc8cb14cf728790e1cf83f3` | `/opt/montara-main-release/main-transition-overlay-20261120` |
| 5 | `60-main-suggest-browser-bridge-20261120.conf` | `81c94bccfabfbec4202e87a87fc8661120a9a303d3727dfe7382dcbac3b8214d` | `/opt/montara-main-release/main-suggest-bridge-overlay-20261120` |
| 6 | `70-main-batch-render-resilience-20261120.conf` | `5977704414ede6e9342e805c44f2dc511ada7f601bbe2e0e841df49a2ee76f7c` | `/opt/montara-main-release/main-render-resilience-overlay-20261120` |
| 7 | `80-main-mixer-channels-20261120.conf` | `1d4d46d98c4c162b55de9cfb8a0924cf83ff9d2c10f6d43e80bd29e0b733ef1a` | `/opt/montara-main-release/main-mixer-channel-overlay-20261120` |
| 8 | `90-main-mix-parity-20261120.conf` | `aaa4be743e3a4e727b0bdf44b630d8b41102a5851c9242f028ce45166b570234` | `/opt/montara-main-release/main-mix-parity-overlay-20261120` |
| 9 | `95-main-pan-ui-20261120.conf` | `e625e46d70deb79f265c39633cacb888d5aa99d0b96e33e01882070ce10198ed` | `/opt/montara-main-release/main-mix-pan-ui-overlay-20261120` |
| 10 | `96-main-range-preview-20261121.conf` | `26f2c9bc6ae912e410c335bcbc2e712597e564193fd6d14080e06d0f50e9cf42` | `/opt/montara-main-release/main-mix-range-overlay-20261121` |
| 11 | `97-main-fast-start-20261121.conf` | `e042155dc56bf13c776c768ff11dc666b58fb0e0267a63fb32e911c3517f12f5` | `/opt/montara-main-release/main-mix-fast-start-overlay-20261121` |
| 12 | `98-main-stable-audio-20261121.conf` | `f7d7cf0ef92394af2cd151f93cc38a0990cc3489b89b073cbdc9c7c1bc7d2956` | `/opt/montara-main-release/main-mix-stable-audio-overlay-20261121` |
| 13 | `99-main-mix-reentry-20261121.conf` | `c7d362c09f044861f6d66620ab723bdc87c8009e5b0c706b4d835ddb1e9cea45` | `/opt/montara-main-release/main-mix-reentry-overlay-20261121` |
| 14 | `zzz-main-30-song-recovery-20261121.conf` | `923fa57e3b6cfbad68212fb2e30a37037e563eb731d169bbfd984f8afc276927` | `/opt/montara-main-release/main-30-song-recovery-overlay-20261121` |
| 15 | `zzzz-main-single-inventory-20261121.conf` | `0323f5aed909adda7eaefba337fc813c8b60cec8ab2079748a48a3da49e3b893` | `/opt/montara-main-release/main-30-song-single-inventory-overlay-20261121` |
| 16 | `zzzzz-main-local-downloads-20261121.conf` | `eb14c5cb5c9388686cd1b2893a92d82afd649fadda93095006a903e66eec98fd` | `/opt/montara-main-release/main-local-project-download-overlay-20261121` |
| 17 | `zzzzzz-main-ranged-download-20261121.conf` | `2965e99000148fcf5d626a1fff225083d1db2f7dbaffc186582315f87cec0ca4` | `/opt/montara-main-release/main-ranged-download-overlay-20261121` |
| 18 | `zzzzzzz-main-download-scope-20261121.conf` | `31c5a6f6f5c2e4568bcb29a0526ccd4874d5b5876188177a5277f043cd893684` | `/opt/montara-main-release/main-ranged-download-scope-overlay-20261121` |
| 19 | `zzzzzzzz-main-project-name-20261121.conf` | `32b15c6fe3fcffa70914e3f3d50b1f1f67c7988fee52c971f945f7d27cb789cd` | `/opt/montara-main-release/main-project-name-overlay-20261121` |
| 20 | `zzzzzzzzz-main-jm-approved-20261122.conf` | `495ad32a42f335bd178b8f4e4084a4c9201383df3931765df2288ca153f460d0` | `/opt/montara-main-release/main-jm-approved-mixer-20a201d` |
| 21 | `zzzzzzzzzzzzz-main-logo-20261122.conf` | `da57c9c3f92107d4a39ef9cdb8775235a29ed9686bafacc78e0c9d77cd0dda8b` | `/opt/montara-main-release/main-approved-logo-20261122` |
| 22 | `zzzzzzzzzzzzzz-main-spherical-20261122.conf` | `5ba3c7a22b988ccce79a6befdcf59a7184cab5342b407eb262a2254317ee5d73` | `/opt/montara-main-release/main-approved-360-20261122` |
| 23 | `zzzzzzzzzzzzzzzz-main-review-20261123.conf` | `6c75415998428dfb238faa8b09479714ccaef07d0503c45d9314e2d2169174db` | `/opt/montara-main-release/main-review-timeout-20261123` |
| 24 | `zzzzzzzzzzzzzzzzz-main-frames-20261123.conf` | `89fa1c1d0ba14e89f31d6612f1f01b42b07593a4ef43a096f79d3906e889cc97` | `/opt/montara-main-release/main-reviewed-frames-20261123` |
| 25 | `zzzzzzzzzzzzzzzzzz-main-edit-save-20261123.conf` | `5c868af6f25fc1b5d2d1b833ec798bdb58d5eaacd61091ccf3fb18c57c4b3c25` | `/opt/montara-main-release/main-edit-save-20261123` |
| 26 | `zzzzzzzzzzzzzzzzzzz-main-six-stage-20261123.conf` | `cfee2e52a44a8b39f66f14e6a50faec65d0fc0fc3f8e7710f29462141e1086a1` | `/opt/montara-main-release/main-six-shot-stage-20261123` |
| 27 | `zzzzzzzzzzzzzzzzzzzz-main-six-editable-20261123.conf` | `245c99dbf15ae107d9dc5504b36f20830f1a0b35c26e5dd27340c5b545b2e929` | `/opt/montara-main-release/main-six-editable-20261123` |

## Change provenance / maturity

| Scope | Trace | Status per recorded evidence |
|---|---|---|
| Selective JM Mixer + projects | #382, #387 | Accepted by JM; merge recorded; live baseline with later overlays |
| Logo | #389 | LIVE OVERLAY; standalone PR still open |
| 360 POV | #390 | LIVE OVERLAY; separate missing-start issue #396 unresolved |
| Stage review transport timeout | #393 | LIVE OVERLAY; does not speed Engine |
| Private JPEG thumbnails | #394 | LIVE OVERLAY; authenticated visual check outstanding |
| Edit/Save socket timeouts | #395 | LIVE OVERLAY; not an end-to-end guarantee |
| Six editable shots | #397 | LIVE OVERLAY; synthetic QA passed, human UI verification pending |
| LAB Stage parity | #359, #383 | DRAFT / LAB ONLY, not deployed to MAIN |
| R2 quotas and migration | #324, #325, #370, #391 | DRAFT / PILOT; not live user storage |
| GitHub Actions | #372 | BLOCKED before runner; not passing CI |

## Gates still required before a reproducible MAIN release

1. From an independently approved read-only runtime probe, resolve every referenced release directory to **git tree or exact file-set SHA-256**, module import origin/precedence, WSGI path, full Engine and Mixer commits actually loaded, and overlay builder/rollback identifiers. This inventory hashes the *drop-in configuration files*, not the full released code trees.
2. Record service version and exact controlled request path Worker → tunnel/VPC → portal/broker/Engine (without tokens, keys, OAuth IDs, private Owner paths); compare against #367 and installed Mac/Windows Companion protocol.
3. Map every layer to its PR and compare file precedence; classify duplicated/superseded code without removing or reordering systemd drop-ins. Produce a SHA-pinned build artifact and rollback with smoke, regression and differential FER Windows checks.
4. Obtain explicit FER+JM agreement in #392 before shared infra/MAIN release changes; never infer approval from a review comment or a green `/health`.
5. Resolve #396 start-of-360 source coverage and verify first six editable shots before any new user render; do not alter an original or audio sync by guesswork.

**No changes performed** to live services, Cloudflare, billing, secrets, projects, database, media, or Engine/Companion. This is an audit checkpoint, **not** a complete certified runtime manifest.
