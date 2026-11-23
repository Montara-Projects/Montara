# Montara H4 dynamic CPU governor — deployed 2026-11-23

## Deployment facts
- VM: Google Cloud montara-test, `e2-standard-8`, 8 vCPU, 31 GiB RAM, **no attached GPU**.
- Root-owned script: `/opt/montara/operator/owner_cpu_governor.py`.
- Root-owned timer: `montara-owner-cpu-governor.timer` (runs every 10 seconds).
- Root-owned oneshot: `montara-owner-cpu-governor.service`.
- No broker restart, Engine restart, project mutation, or user file changes.
- Systemd runtime quotas are applied only to matching verified H4 worker services and exact system.slice cgroups. They are not permanent settings in the underlying Engine unit generator.
- Before deployment, JM had `CPUQuota=100%`, three MAIN jobs `CPUQuota=500%` each. Four current workers were idle (no FFmpeg); first governor pass normalized to `100%` each. Later calls update limits based on measured cgroup CPU demand.
- Broker launch profiles remain unchanged: jmlab=100%, main=500%, fertrial=100%, betamain=250%; governor corrects quota of any new verified worker as soon as it runs. A future broker integration can make initial admission resource-safe before the first 10s tick.

## Scheduling policy
- Reserve 100% = one vCPU for OS and services.
- Cap any actively busy owner worker at 600% = six CPUs.
- If 1 of 4 workers busy: 600% busy, 25% per idle worker (sum 675%).
- If 2 busy: 325% each and 25% per idle worker (sum 700%).
- If 3 busy: 225% each with 25% remaining (sum 700%).
- If 4 busy: 175% each (sum 700%).
- Demand sampled via verified cgroup cpu.stat CPU usage delta; 7% core threshold; hold for 20 seconds to prevent quota oscillations. No GPU assumed.
- No worker stopping/freezing, no memory-limit changes, no access to owner media, no untrusted API inputs.
- Runtime quota redistribution may lag by roughly one timer cycle after a load change.
- CPU quota is a ceiling. Single-threaded FFmpeg can still use only one core even when allowed six.

## Tests and verification
- 6 governor safety/allocator tests, 5 earlier pure capacity planning tests.
- `systemd-analyze verify` passed.
- First root-run set-property succeeded on three MAIN jobs and verified the service stayed active; H4 brokers intact.
- Verified timer was active and scheduling every 10 seconds; journal showed periodic successful plan execution.
- Engine retained its existing bundle, private Owner sessions and data unchanged.

## Important remaining work: true global admission queue
The live governor adjusts **CPU**, but does not prevent several brokers from starting jobs that could collectively exceed the 31 GiB RAM budget. The requested **fair waiting queue** is therefore **not yet fully implemented**.

Next separate root-broker change:
1. Cross-broker trusted admission ledger keyed by exact H4 owner+job identity.
2. Per-worker memory reservations, global hard memory budget and FIFO queue.
3. Idempotent lease renewal, owner disconnection policy, cancelled job removal.
4. Atomic reservation before systemd worker start; release only after verified cgroup termination.
5. Distinct JM, FER, MAIN isolation tests and concurrent real-session QA.

## Monitor
```sh
systemctl list-timers | grep montara-owner-cpu
journalctl -u montara-owner-cpu-governor.service -n 20 --no-pager
systemctl show '<validated-job>.service' -p CPUQuotaPerSecUSec
cat /sys/fs/cgroup/system.slice/<validated-job>.service/cpu.max
```

## Emergency rollback (operator only)
1. `sudo systemctl disable --now montara-owner-cpu-governor.timer`
2. For all currently running, *verified* workers, restore the operator's H4 broker profile with `systemctl set-property --runtime`; current values at deployment: JM 100%, MAIN 500%, FERTRIAL 100%, BETAMAIN 250%. This does **not** restart workers.
3. Check that timer is inactive and all brokers/workers remain online.
4. Keep the script and unit files for audit rather than deleting them during troubleshooting.

Do not use `systemctl stop` against an Owner job to change quotas. Do not restart brokers as part of this feature.
