# Issue #305 — Broker construction, daemon exclusivity and safe recovery

## Root cause / incident

An ad-hoc DemoBroker constructor ran ledger.recover_after_restart() inside its constructor. That broad sweep marks all unfinished jobs in a shared ledger orphaned, including live jobs of other Owners; the constructor then attempted stop_verified on each. As observed on MAIN on 2026-11-20, this could stop another Owner's active Engine.

## New startup contract

- DemoBroker.__init__: creates a trusted handler without reclassifying, stopping or inspecting existing running jobs. An operator helper can construct it without touching a live Owner's Engine.
- main is the only entrypoint that obtains a private, non-symlink, root-owned exclusive flock on the ledger directory. The file descriptor remains open for the entire daemon lifetime and is non-inheritable by exec.
- A second daemon is rejected if the lock is held. Additionally, it refuses to unlink a currently listening Unix socket, even when upgrading from an older daemon version that did not hold the new lock.
- Only this guarded authoritative daemon calls reconcile_on_authoritative_start.
- Startup enumerates unfinished generations read-only. Loaded active systemd units remain untouched and their jobs stay running. A transient unit can be released only after double-checking exact persistent unit identity, LoadState=not-found, inactive/dead/zero PID, no control group and absence of its cgroup twice.
- If a unit is loaded, status is uncertain, target ID is missing or generation changes while checking: do nothing, preserve the owner fence for safe operator investigation. Startup does not call systemctl stop.
- The former JobRecoveryLedger.recover_after_restart is legacy low-level code used by existing isolated tests; it is no longer used by the daemon constructor or service. It must not be called from operator renewal tooling. Use the authoritative broker's trusted IPC interface for Owner-scoped operations.

## Test evidence (isolated / no live host writes)

tests/test_broker_authoritative_recovery_305.py uses real SQLite owner/generation fencing and mocked systemd, exercises:
- two live owners retained on restart, continued same-project admission;
- a distinct missing unit released after independent absence proof;
- loaded unit, unbound target, ambiguous systemd state, cgroup still present, ledger race;
- constructor cannot invoke broad recovery/stop;
- exclusive daemon lease, cross-process lock, live Unix socket protected, symlink/invalid path rejection.

Existing Owner/VM tests additionally verify original admission and recovery contracts.

## Release gates

- [ ] JM and FER review code and isolation assumptions in the draft PR; do not merge or deploy automatically.
- [ ] GitHub Actions CI runners restored (separate #372) and full broker security suite green.
- [ ] Isolated VM sandbox with two synthetic Owners and their exact systemd/cgroup identities; construct a helper broker, restart authoritative broker, prove both remain active and ledger generations unchanged. Never run this on MAIN/FER live workers without explicit maintenance window.
- [ ] Verify crash restart and stale missing-unit recovery with journal evidence; preserve rollback and ensure no unrelated Owner release.
- [ ] Controlled rollout to LAB-JM first, then FER and MAIN only by joint approval, no active renders. Recheck original projects, authenticated editor and Companion after restart.

Status: code + unit/integration mocks tested locally, no production services restarted or original media changed. #305 should remain In Progress until independent VM and human acceptance gates pass.
