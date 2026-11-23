# H4 global RAM admission queue and Owner fairness — 2026-11-23

## Status
**Source implementation prepared; NOT activated on the VM.** Existing CPU governor
with two reserved and six shareable vCPU remains LIVE and unchanged.
This is a separate, operator-gated cross-broker admission release.

## What the candidate implements

- A single shared root-only SQLite FIFO reservation ledger. All H4 brokers
  (JM, MAIN, FERTRIAL, BETAMAIN) use the *same* file when the operator enables
  the optional `--global-admission-db` argument. Default broker behavior is
  unchanged until explicit provisioning.
- Fixed RAM reservation budget: 24 GiB of the 31 GiB VM, leaving about 7 GiB
  for operating system, caches, service processes and transient spikes. A
  worker reserves its configured MemoryMax in GiB, rounded up, before starting.
  JM currently 6 GiB, MAIN 8 GiB, FERTRIAL 1 GiB, BETAMAIN 4 GiB.
- First-in-first-out requests; capacity cannot be overbooked. Different
  Owner accounts cannot read each other's IDs or queue records. Each Owner
  may have multiple waiting requests but **only one admitted worker** across
  brokers with the same canonical trusted owner key, so several renders from
  one person cannot steal multiple CPU shares.
- Owner awaiting resources receives HTTP **202** with authenticated queue
  position, private no-store headers and Retry-After: 5s. Browser displays
  'Your job is queued · position N', polls at 5s, then proceeds automatically
  when admitted. No invented wait estimate; measured ETA is future work.
- Cancelling an unstarted job removes only the queue entry. A started or
  orphaned job retains its reservation until the broker independently checks
  the exact systemd unit and cgroup empty. Broker restart preserves queued
  unlaunched records and fences uncertain started jobs.
- The source path is feature-flagged; legacy brokers are not silently changed.

## Verified in source-only tests

- 14 Python tests of concurrent SQLite admissions, RAM capacity, FIFO,
  per-owner pending renders, cancellation, foreign-owner denial and
  orphaned/verified-release paths.
- Integration tests for queued broker status and restarting an unlaunched
  job, gateway position-only response contract, browser queue status.
- Mocked browser 202->202->200 -> authenticated upload succeeded.
- Existing H4 broker isolation and browser bridge/multitab tests pass.

## Why activation requires a coordinated gate

Four pre-existing live resident jobs were observed:
one JM with 6 GiB MemoryMax and three MAIN workers with 8 GiB MemoryMax
each, **30 GiB reserved by their existing unit limits**. If the new
24-GiB reservation DB starts empty while these workers remain active, the
ledger would incorrectly think the RAM is free. If we restart H4 brokers
without draining, their own ledger's startup recovery can orphan/stop
running workers. **Do not restart brokers while any Owner job is active.**

To deploy safely:
1. Verify all current user edits/renders have finished and all H4 Owner
   workers have been closed through their normal, verified shutdown path;
   merely closing browser tabs is NOT a proof of worker termination.
2. Confirm no verified H4 job services, unverified ledger entries or
   populated cgroups remain. Explicitly retain user media/project disks.
3. Create `/var/lib/montara-global-admission` owned root:root, mode 0700,
   shared by all intended root broker services. The directory must be
   writable only from the trusted broker unit via a narrow systemd
   ReadWritePaths policy; do not expose SQLite files to the web user.
4. Enable matching `--global-admission-db=/var/lib/montara-global-admission/jobs.sqlite3`
   and `--global-admission-capacity-gib=24` on **every** eligible broker.
   Never opt in just one broker while other brokers can still create
   reservations outside the global database.
5. Prepare an authenticated, pinned browser/portal build carrying the queue
   202 UI and Owner gateway 202 route. Restart brokers only after proven
   empty state; verify initial WorkerResourceProfile and operator limits.
6. Test multi-owner concurrent admissions with actual worker launches,
   cancellation, restart recovery, real 360 export, RAM usage and queue
   position privacy. Check CPU governor still caps global quota at 600%.
7. Roll back only after safely draining the queue/reservations, to avoid
   orphaned global leases. No deletion of saved videos/projects.

## Remaining qualifications

- Existing per-instance JobRecoveryLedger permits one unfinished worker
  per Owner in each H4 namespace. Multiple queued requests from one Owner
  can be represented in the global ledger but same-instance second-work
  submission needs a separate local multi-job ledger migration.
- Cross-broker fairness assumes the validated `owner_id` is the same
  canonical identity in all H4 namespaces. Confirm this by trusted identity
  tests before enabling multi-namespace admission; avoid exposing Google
  IDs or relying on browser-supplied ownership labels.
- CPU fair sharing is the existing live governor; queue admissions are
  based on reserved RAM, not arbitrary CPU thresholds. With 24 GiB reserved,
  twelve simultaneous RAM-heavy renders would be queued, even though
  12 x 50% vCPU is mathematically possible.
- A wait-time estimate requires historical runtimes by job class and should
  show a range with uncertainty, never an invented five-minute figure.
