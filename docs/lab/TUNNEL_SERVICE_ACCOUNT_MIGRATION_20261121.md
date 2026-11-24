# Shared Cloudflare tunnel — migration plan before retiring fgardel00

Ticket: #334. Joint FER/JM review required. No deployment, secret movement, user deletion or tunnel change is part of this PR.

## Why the account cannot simply be deleted

On GCE montara-test, old interactive Linux user fgardel00 (UID 1006) owns the running cloudflared process. It also runs the former Owner/FER integration user-level services on loopback 8115, 8116, 8126. The user unit names include montara-owner-tunnel.service, montara-owner-beta.service, montara-owner-h4-native.service and montara-lab-fer-portal.service. Old broker BindReadOnlyPaths reference portions of this home.

The Cloudflare account contains separate Workers for MAIN, LAB-JM, LAB-FER and legacy Owner. Some Workers and VPC services share a tunnel. Do not assume old services or routes are unused just because a new Worker exists. Project-wide GCE SSH keys currently include ubuntu and fgardel00; ubuntu was separately verified for SSH + sudo. A removal operation must also update GCE SSH keys or the guest agent can recreate the local user.

The existing MAIN service identity is montara-main with nologin; this is not an interactive human. The shared tunnel should NOT be owned by MAIN if FER and JM depend on it. The preferred new service owner is a dedicated nologin identity such as montara-tunnel, unless a documented privilege-isolation check approves an existing neutral technical account. This would not be a fourth product user.

## Work split / acceptance gates

1. FER explicitly reviews #334 and identifies his remaining dependencies on the old integration ports, SSLIP #318, staging236 and any home-folder paths. JM maps Cloudflare Worker names, the VPC-service destination for each, tunnel connector and GCE process/service with no credentials in repo.
2. Produce a small code/config PR for an independently installed and version-pinned cloudflared under systemd system scope. New identity must have nologin, no sudo/SSH, read-only access to only one root-managed credential, minimal write paths and explicit restart/rollback documentation.
3. Do not copy token plaintext into GitHub, test logs or an accessible home. Never modify live OAuth/Worker/VPC in order to satisfy a simple file cleanup. Back up any required operational config without publishing it.
4. Verify that running two connectors on the same tunnel will not alter or break routing before any overlapping deployment. Blue/green transition with positive/negative auth checks: MAIN, JM, FER, legacy Owner still required, OAuth start/callback, CSRF 401/403, upload and Companion loopback.
5. Only after FER approval, owner approval and repeated health checks: retire user-level tunnel and old Owner services one by one, keep recorded rollback, check fresh client sessions and watch for service regressions.
6. Once the tunnel is running independently and legacy home references have been removed, revoke fgardel00 project/instance SSH keys, remove its interactive user/home, verify guest agent does not recreate it, and record disk savings. Do not remove FER media or test fixtures during this step.

Rollback: leave current fgardel00 tunnel running until the replacement is validated; preserve a tested path to restart the prior connector if deployment fails. If any environment fails negative or positive auth test, stop the new connector and restore old configuration before deleting anything. Never remove credentials and old account before rollback assurance.

References: #334, #216 coordination, #318 SSLIP cleanup, #331 VM storage audit, #332 read-only T4T test fixture.

## Independent cleanup already completed 21 November 2026

The users amehc_gracia and macbookair were removed only after verifying no service/process dependencies on their home and confirming ubuntu as an alternate GCE SSH+sudo administrator. Their project-level SSH key entries were removed from project metadata, preserving fgardel00 and ubuntu. MAIN/JM portal and broker services remained active. 4.3 GiB was recovered from macbookair home, root free now about 15 GiB on 96 GiB disk. These removals are not a reason to delete fgardel00 prematurely.
