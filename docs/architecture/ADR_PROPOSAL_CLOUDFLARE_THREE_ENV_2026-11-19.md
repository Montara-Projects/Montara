# ADR proposal — MAIN + LAB-JM + LAB-FER: three isolated environments, shared Cloudflare connectivity where safe

**Status:** PROPOSED / JOINT REVIEW REQUIRED (FER → JM). **Date:** 2026-11-19. **No deployment authorization.**

## Product intent and non-negotiable outcomes

Fernando confirms that **MAIN, LAB-JM and LAB-FER run on the same Google VM, under different operating-system users**. The purpose of LAB-FER and LAB-JM is to test changes against an architecture representative of MAIN so that promoting a validated fix is simple, controlled and reproducible. The goal is **three independently addressable environments, not necessarily three independent Cloudflare tunnels**. No shared mutable project data, Engine/broker leases, sessions or cookies between environments.

**Important distinction:** Cloudflare Tunnel (`cloudflared`), a Cloudflare Worker, a Workers VPC `vpc_service` binding, a hostname/route and the backend process are different resources. Sharing one transport/tunnel is possible, but does not prove isolation or even that current Workers use that tunnel. Avoid inferring topology from names.

## Evidence snapshot (read-only Cloudflare API, 2026-11-19)

- Cloudflare Tunnel `montara-owner-fg` exists and is `healthy`, with four connections reported. Its relation to the three Workers and actual VM origin is **not yet verified**; tunnel configuration inspection did not yield an ingress mapping.
- Workers `montara-owner`, `montara-owner-h4`, `montara-lab-fer` exist. Each exposes a binding named `OWNER_PRIVATE_API` with type `vpc_service`. **A common binding name does not establish a common backend or common tunnel**. Need inspect actual binding targets, routes, access policies and versions.
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
