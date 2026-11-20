# ADR proposal — MAIN + LAB-JM + LAB-FER: three isolated environments, shared Cloudflare connectivity where safe

**Status:** TO-BE architecture technically ACKed by JM; controlled isolated MAIN preparation authorized verbally by Chema to FER on 2026-11-20. **The historical deployment has NOT been replaced; new OAuth portal and public MAIN are NOT live.**

## Product intent and non-negotiable outcomes

Fernando confirms that **MAIN, LAB-JM and LAB-FER run on the same Google VM, under different operating-system users**. The purpose of LAB-FER and LAB-JM is to test changes against an architecture representative of MAIN so that promoting a validated fix is simple, controlled and reproducible. The goal is **three independently addressable environments, not necessarily three independent Cloudflare tunnels**. No shared mutable project data, Engine/broker leases, sessions or cookies between environments.

**Important distinction:** Cloudflare Tunnel (`cloudflared`), a Cloudflare Worker, a Workers VPC `vpc_service` binding, a hostname/route and the backend process are different resources. Sharing one transport/tunnel is possible, but does not prove isolation or even that current Workers use that tunnel. Avoid inferring topology from names.

## Evidence snapshot (read-only Cloudflare API, 2026-11-19)

- Cloudflare Tunnel `montara-owner-fg` exists and is `healthy`, with four connections reported. Its relation to the three Workers and actual VM origin is **not yet verified**; tunnel configuration inspection did not yield an ingress mapping.
- The historical snapshot counted three Workers. **Superseded by live five-Worker inventory below.** Their shared binding name alone never proves a shared backend or tunnel.
- Repository `docs/lab/STATUS-JM.md` (2026-11-17 observations) describes LAB-JM `:8101`, LAB-FER `:8102`, MAIN `:8103` as distinct services, plus legacy Owner `:8115`, H4 `:8116`, FER trial `:8126`, and Work-related staging. Those observations are **historical**, not current port ownership or approval to reuse them.
- Repository `docs/lab/STATUS-FER.md` documents a functioning FER Stage/Windows E2E and FER portal `:8126` at that checkpoint. Preserve it until mapped and backed up.
- `docs/integration/H4_OWNER_PREFLIGHT.md` and `H4_VERCEL_GCE_STAGING.md` require H4 staging to isolate Owner directories, broker/socket/ledger, OAuth origin/client and rollback; **H4 is an isolation architecture label, not proof that `montara-owner-h4` is MAIN**.
- Chema requested the three-entry topology as a priority in issue #216. No changes to Cloudflare or VM are authorized by this proposal.

## Recommended target architecture (subject to JM audit)

1. **Three stable HTTPS origins**, one each for MAIN, LAB-JM and LAB-FER. Each has an explicitly owned edge entrypoint (Worker/route if needed), an explicit mapping to its backend and a health/version endpoint. Avoid using accidental `workers.dev` aliases as canonical origins if OAuth requires exact callback origins.
2. **One shared private connectivity layer only if verified safe**: a single healthy Cloudflare Tunnel may serve several ingress routes/hostnames to different localhost services, *or* the existing Workers VPC private-service mechanism may be the correct transport. Select based on actual Cloudflare and VM inventory, not naming or assumed equivalence. Do not add an unnecessary second networking layer.
3. **Isolation on the same VM**: distinct systemd units, listening ports or sockets, Unix service users where feasible, writable data directories, SQLite DBs, broker/Engine worker namespaces and ledgers, locks, temp/cache paths, job queues, logs and retention scopes. Shared read-only code artifacts/Engine/Mixer pins are acceptable if explicitly versioned and verified; never share writable mutable state.
4. **Identity/security**: separate session cookie scopes per HTTPS origin; exact OAuth redirect URIs registered and validated for each environment (separate clients where justified by existing H4 contracts); CSRF, Google owner binding, private project isolation, and access allowlists preserved. Labs must not accidentally use MAIN credentials or session DB. Private lab routes require appropriate access control, not merely obscure URLs.
5. **Promotion contract**: main branch / pinned release is reference; labs run reproducible versioned deployments of the *same architecture* with isolated config/state. Changes travel via PR → CI → lab E2E → review → controlled MAIN promotion, with explicit version and rollback. No direct copy of lab SQLite/session state into MAIN.
6. **VM resource limits**: because all three environments share one machine, set per-service resource/concurrency controls and account for Engine/broker contention. Isolated users/ports alone do not prevent resource interference.

Conceptual routing (NOT asserted as deployed):

```
MAIN HTTPS origin     → edge MAIN     ─┐
LAB-JM HTTPS origin   → edge LAB-JM   ─┼→ verified private connectivity → isolated MAIN/JM/FER services on same VM
LAB-FER HTTPS origin  → edge LAB-FER  ─┘
```

## Mandatory joint audit before choosing `owner` versus `h4`

JM AI: please return an evidence table for **each** of `montara-owner`, `montara-owner-h4`, `montara-lab-fer`, `montara-owner-fg` and the three candidate VM services: actual URL/route, binding destination, tunnel/VPC relationship, process+port/socket, Unix user, deployed commit/bundle, OAuth callback, cookie scope, session/SQLite location, Engine/broker/ledger namespace, access control, health, dependencies, and rollback. Mark **UNKNOWN** where evidence is missing. Check current runtime, not just README or historical STATUS. No secrets or user emails in public issues/PRs.

Explicitly answer:
- Is `montara-owner-h4` staging/legacy or a candidate for MAIN? What currently uses `montara-owner`? Which of these is safe to preserve, repurpose or retire, and on what evidence?
- Does `montara-owner-fg` actually carry any of these Worker requests, or do Workers reach origins via Workers VPC independently?
- Can we use **one shared connectivity path** with independent routing and state, or would it create a security/availability coupling? Recommend the smallest safe design.
- What will happen to existing Owner/H4/FER trial/Work/Multisong routes and active jobs during any migration?
- Which DNS/HTTPS hostnames and Google OAuth redirect URIs are registered, and which must be added before a cutover?

## Gate / requested response

**This PR is documentation-only.** No Worker, Tunnel, VPC binding, DNS, OAuth, systemd, service, data or deployment change; no automatic merge. JM AI should comment with (1) verified as-is map, (2) recommended to-be map and tradeoffs, (3) minimal migration steps and isolated rollback per environment, (4) risks and acceptance checks (three distinct sessions, cross-environment denial, Engine isolation, healthy MAIN throughout), and (5) open decisions requiring both humans. FER AI will review. Only then seek explicit Chema + Fernando approval before changing shared infrastructure.

References: issue #216; `docs/lab/STATUS-JM.md`; `docs/lab/STATUS-FER.md`; `docs/integration/H4_OWNER_PREFLIGHT.md`; `docs/integration/H4_VERCEL_GCE_STAGING.md`.

## Verified AS-IS update — 2026-11-20 (FER/JM)

This section supersedes the original snapshot where it conflicts. The Cloudflare inventory and independent JM review in PR #279 establish **five Workers**, not three.

| Worker | Runtime/backend mapping | Evidence / certainty |
| --- | --- | --- |
| `montara-lab-fer` | FER isolated lab; VM loopback `:8126` listener | Worker has its own VPC service binding according to JM API inventory; specific worker-to-process live E2E still unverified |
| `montara-lab-jm` | JM isolated lab; VM loopback `:8130` listener, service `montara-h4-jmlab-portal` | Separate VPC binding; JM has confirmed private HTTPS login flow, not FER end-to-end |
| `montara-owner` | Historical Owner | Preserve; exact current process/port-to-VPC mapping requires further inspection (UNKNOWN) |
| `montara-owner-h4` | Historical Owner/H4 | Preserve; do not relabel as MAIN; exact current process/port-to-VPC mapping UNKNOWN |
| `montara-main` | **Placeholder 503, no backend** | Verified Cloudflare `bindings=[]`, workers.dev subdomain `enabled=false`; not a functioning portal |

**Shared resources:** Cloudflare's four legacy Workers use four **distinct VPC services**; this does not imply a separate Tunnel per environment or prove all state isolation. No existing Worker/binding was renamed, connected or removed. The historic `montara-owner-fg` Tunnel is present but exact relation to the VPC paths is still UNKNOWN.

**VM read-only observations:**
- `montara-main.service` runs a historical preview as Unix user `montara-main`, Gunicorn on `127.0.0.1:8103`, with `/home/montara-main/app` and env file `/home/montara-main/main.env`. **Preserve and do not repurpose.**
- `montara-h4-betamain-portal.service` uses `:8129`; it is a separate historical BetaMain service and **not canonical MAIN**.
- LAB-JM `:8130`, LAB-FER `:8126` are distinct active loopback listeners. The entire machine had approximately 17 GiB available of 96 GiB at this checkpoint (83% used): no indiscriminate bundle duplication.
- The current GitHub `main` SHA observed was `051c58130ad512aa05e841effc4f5651ca04a188`. This is a **candidate reference**, not a release certified by E2E, and must not be deployed automatically on every commit.

## Joint decision and preparation evidence — 2026-11-20

JM technically ACKed **a new isolated OAuth MAIN portal**, explicitly rejecting reuse of preview `:8103` or BetaMain `:8129` (PR #279 JM ACK). FER reports Chema's explicit **verbal approval by telephone** to proceed with the jointly agreed isolated MAIN rollout. This is FER's report of human consent, not a purported signed GitHub response from Chema. No authority to wipe or alter other services, data, credentials or historical routes is inferred.

**Actual non-disruptive preparation completed on the VM (FER IA via SSH, confirmed by stat/getent/systemctl):**

- New Unix system identity `montara-release-main`, UID 985 at checkpoint, home `/var/lib/montara-release-main`, shell `/usr/sbin/nologin`.
- `/var/lib/montara-release-main`, with `data/cache/sessions/jobs`: owned by dedicated identity with mode **0700**.
- `/etc/montara-release-main` and `/opt/montara-main-release`: root-owned, group `montara-release-main`, mode **0750**.
- `/opt/montara-main-release/CANDIDATE_MAIN_SHA`: root-owned group-readable **0640**, stores candidate SHA only.
- **No live MAIN OAuth portal, new systemd service, selected listening port, copied Google JSON, private Worker VPC binding or workers.dev activation yet.** All existing sampled services remained active after the preparation.

**Next gates (in order):** (1) validate the candidate code's actual OAuth portal factory/configuration and choose a free port with a documented namespace, (2) install a minimal pinned **read-only** release under the new directory without copying historical writable lab state, (3) bootstrap private sessions/SQLite/broker+bounded Engine state under the dedicated identity and keep secrets out of the code tree, (4) move the *user-owned* MAIN Google OAuth JSON from Windows only via confidential verified transfer, install to a private file and remove any temporary server upload, (5) isolated HTTP tests for unauthenticated 401, OAuth redirect 302, cookie/CSRF, multiple authorised users and negative cross-environment tests, (6) atomically connect Worker MAIN to an exclusive verified VPC service and enable the hostname, with saved previous settings and rollback, (7) human Stage → local Companion → real MP4 on Windows (FER) and Mac (JM). Never confuse preparatory evidence with full E2E.

**Owner boundaries:** FER accepts Windows Companion QA, JM accepts Mac Companion QA. Shared HTTP and security contracts only. LAB-FER/LAB-JM are two trusted developers' private workspaces; normal protection against outside websites remains mandatory, and a later dedicated whole-product security phase is planned before wider access.

## Ordered migration and retirement contract — FER confirmation 2026-11-20

**User decision:** do not start by cleaning or migrating historical services. First establish and validate all **three** distinct Cloudflare entrypoints (MAIN, LAB-FER, LAB-JM), then migrate only verified dependencies/state, and **only then** retire obsolete VM assets, edge workers/routes and Google OAuth clients/redirect URIs. Retirements need owner approval, evidence of no active sessions/jobs, backup, rollback and explicit confirmation of every dependent consumer. No blind deletion or automatic revocation. The current separate JM and FER VM-space audit tasks and OAuth inventories in GitHub Projects remain the source of individual inventories; this ADR defines their joint migration gate.

**OAuth retirement inventory must include:** Google Cloud project/client ID (never secret), owner (JM/FER/MAIN/legacy), exact registered JavaScript origins and authorized redirect URIs, active Worker/route + portal backend correspondence, last verified usage and dependency evidence. Record KEEP / MIGRATE / RETIRE_CANDIDATE / UNKNOWN; UNKNOWN never authorizes revocation. Remove old redirect URIs/clients only after both real browsers can log into MAIN and their lab, after rollback window closes and explicit operator confirmation. MAIN Google OAuth JSON remains on FER's Windows machine until private backend provisioning.

**Code contract correction, verified from current main SHA 051c58130ad512aa05e841effc4f5651ca04a188:** `H4Instance('main')` derives Owner root **`/var/lib/montara-h4-main-owner`**, broker ledger **`/var/lib/montara-h4-main-broker/jobs.sqlite3`** and owner-admission socket **`/run/montara-h4-main-owner-admission/control.sock`**. Do not invent a different Owner root for its factory. FER created the exact private Owner root (0700, owned `montara-release-main`) with private `data/cache/sessions`; `/var/lib/montara-release-main` remains preparatory staging only. Collisions on the new `h4-main` service paths were checked absent. Existing services unchanged. The factory also requires a verified immutable editor/Engine manifest and live matching broker; these gates are **not yet passed**. No new portal or broker service was started.

## MAIN release source + broker trust boundary — preparation 2026-11-20

- Reused existing **root-owned immutable** Engine bundle `engine-92c7bc33f59baae92a8d61e5dd4bf0ce9685d79e` (~1.4 GiB) because `main` SHA `051c581...` gitlink resolves to the exact same revision. Reused pre-existing editor bundle `jm-eff91bd8dd69d750601e7146b3a997bea2edce1f` (~190 MiB) **read-only** after verifying its manifest: matching Engine 92c7, Mixer pin and existing preview quota 2048 MiB. `verify_pinned_chema_manifest` and `verify_jm_bundle_files` passed as the new MAIN Unix account. This is immutable code reuse, **not permission to reuse LAB-JM cookies, broker sockets or databases**.
- Staged only `urano/` and `deploy/` from **exact GitHub `main` commit 051c58130ad512aa05e841effc4f5651ca04a188** to `/opt/montara-main-release/source-051c58130ad512aa05e841effc4f5651ca04a188` (572 KiB, root:montara-release-main, 0550 dirs / 0440 files, no symlinks). It is a frozen candidate source, **not an online portal** or a fully accepted release.
- Found pre-existing release/code mismatch: native H4 worker in that main commit advertises old Engine `b867b3c...` while gitlink and immutable VM bundle are 92c7. Existing JM broker had a private 92c7 correction but MAIN must be reproducible from reviewed GitHub source, not copied from the live lab. Created draft [PR #286](https://github.com/Montara-Projects/Montara/pull/286) HEAD `4e5e1de` to reconcile worker pin and add gitlink contract regression (8/8 focal PASS); pending review, merge and fresh release SHA before starting new broker.
- Prepared distinct system users `montara-release-main` (portal web UID **985**) and `montara-main-trusted` (trusted client UID **984**), both nologin at checkpoint. Broker code explicitly disallows trusted UID = web UID or root. No broker process, account login, systemd unit or public Worker binding enabled. UID values are observations; always resolve with `id` at deployment time, not hardcoded deployment assumptions.
- Broker instance `main` must use **its own** `/run/montara-h4-main-broker/control.sock`, `/run/montara-h4-main-owner-admission/control.sock`, `/var/lib/montara-h4-main-broker/jobs.sqlite3` and root-owned worker script in `/opt/montara/broker-h4-main-native/native_owner_systemd_worker.py`; do **not** point it at JM/FER/Betamain control sockets. Existing worker policy validates approved path and file ownership. Future service must use the corrected/reviewed new release, with pinned resource limits and independent runtime, not copied live service drop-ins.

**Unfinished gates:** PR #286 review, builder/worker provenance and broker namespace QA, private Python dependencies, actual Google MAIN secret handoff/CSRF/OIDC validation, isolated portal local 401/302 and Owner E2E, only then MAIN Worker/VPC. Delay old VM/Google OAuth client + URI cleanup until all three connectors and migration are verified.

## Exact-main candidate and offline unit QA — 2026-11-20

**Version correction:** pre-existing editor bundle jm-eff91bd8 is NOT identical to current GitHub main 051c581 (different app.py and web/montara.js), even though both identify the same Engine gitlink 92c7. Reusing LAB-JM editor without pinning that mixed composition would violate an exact-main release claim.

FER has now staged a dedicated editor bundle from GitHub main 051c58130ad512aa05e841effc4f5651ca04a188 at /opt/montara/bundles/jm-051c58130ad512aa05e841effc4f5651ca04a188. It includes selected application source, web, urano, mixer_adapter, local_media, tools, deploy and dependency manifests (~13 MiB), omitting unrelated fixture/videos/tests. Its patched resumable_upload.py and manifest were generated using the existing same-revision builder, with private quota 2048MiB. The Engine symlink points to the existing immutable 92c7 bundle; the mixer symlink points to a pre-existing root-owned mixer directory whose manifest declares the same f15ff gitlink. **The shared mixer content and the reduced source selection still require acceptance validation.**

Using the actual new MAIN Unix identity, verify_pinned_chema_manifest, verify_jm_bundle_files, verified Engine symlink and prepare_native_owner_runtime PASS. New root-owned H4 MAIN candidate worker source under /opt/montara/broker-h4-main-native (~416 KiB) comes from PR #286 HEAD 4e5e1de (unmerged draft), with immutable root-owned 0444 launcher and the correct 92c7 pin. Exact namespace and worker path checks PASS, while cross-LAB-JM/BetaMain worker paths and mount aliases are rejected. They are preflight checks, not a working Engine E2E.

Two systemd service candidates were staged, **NOT installed or enabled**:
- /opt/montara-main-release/units/montara-h4-main-broker.service: isolated H4 main sockets, ledger, private owner mount, 92c7 Engine and exact-main editor, bounded resources, root broker with a distinct non-root trusted UID and a dedicated web UID.
- /opt/montara-main-release/units/montara-h4-main-portal.service: main web account with private state, initial proposed loopback port 8131 (unoccupied at verification), separate OAuth environment file and shared root-owned read-only Python runtime (avoids duplicating approximately 1.4 GiB).
- /opt/montara-main-release/units/portal.env.example: public origin and pins only, private Google client_id, client_secret and allowlisted emails still missing.

systemd-analyze verify on both offline candidates returned 0, file modes 0440 root:MAIN. Neither service appears under /etc/systemd/system; neither was started. No actual MAIN OAuth portal.env, client secret or new VPC binding. Existing MAIN preview 8103, LAB-FER 8126, BetaMain 8129 and LAB-JM 8130 remain listening; ~17GiB VM available.

**Next explicit gates:** review #286 and historical Engine CI failures; check exact-main bundle selected-source imports and immutable mixer provenance; generate final release SHA rather than running a draft code pin; provision confidential Google OAuth. NOTE: MONTARA_GOOGLE_SECRET_FILE expects a private file containing only the raw client_secret, not the downloaded Google Web OAuth JSON; also obtain its client_id and the explicit email allowlist privately. Then start independent broker/portal, validate 401/302/CSRF and owner isolation, and only after that connect Worker/VPC with rollback. Do not reclaim retired VM/Google OAuth/Worker resources before all three entrances and migration are tested.
## OAuth and broker fail-closed preflight — 2026-11-20

Executed using the dedicated MAIN web account, existing read-only Python runtime and exact staged MAIN editor bundle. A private temporary folder carried a synthetic Google client ID, test address and mode-0600 dummy secret, deleted at the end. No actual user credentials or emails were used.

- validate_beta_settings: PASS, callback https://montara-main.memoriainvalida001.workers.dev/urano/v1/google/callback.
- create_loopback_native_owner_application: correctly DENIED when independent h4-main admission socket absent. Intentional fail-closed.
- Wrong Companion origin, missing client secret file and wrong H4 instance jmlab against MAIN root: all rejected.
- H4 namespace, broker policy, worker args and preflight contracts: 22/22 focal tests PASS in PR #286 worktree; full global CI has Engine failure and is not green.
- Historical preview MAIN, LAB-JM and BetaMain remained active; no MAIN listener was started or Cloudflare changed.

Operator handoff only when deployment ready: Fernando holds secret_main.json on Windows. Never paste it into ChatGPT, GitHub or commits. Provision only actual client_id and private raw client_secret to runtime with verified mode/ownership, confirm matching callback in Google Cloud Console, and remove historical OAuth clients/redirect URIs only after all three sites and migration pass E2E.
