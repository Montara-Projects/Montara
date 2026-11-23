# LAB-JM ingest, progress and capacity — 2026-11-23

NO LIVE CHANGE while Music and I renders. Validated design, not yet authenticated E2E.

## Findings
- LAB-JM runs Engine 9af275b (2026-11-19), exactly the Engine gitlink pinned by Montara origin/main. The standalone zucker_videos main branch (321fdb4, 2026-10-09) and Fer experiment branches are different and are not automatically a reviewed replacement. Recent Montara #386 updates Companion 360 cache, not the server Engine.
- GCP VM: eight Xeon vCPUs, 31 GiB RAM. Current isolated JM worker CPUQuota=100% (one core), MemoryMax=6GiB, cgroup cpu.max=100000 100000. Cgroup recorded 18869 throttled intervals and more than 7231s throttled time. ffmpeg used about one core. Engine IngestStage has up to two proxy workers, but global quota caps them.
- New two small progress rows already show individual videos. The redundant third overall bar has now been removed in this candidate, preserving the existing progress ring.
- Pre-ingest cannot safely start the full Engine stage merely on Drop: that stage currently requires a registered project and audio master, while Continue may change selected cameras. It must be separated into project-independent owner-scoped prewarm and project-specific sync.

## Capacity calculation prepared, NOT activated
- Pure operator-only policy in urano/owner_capacity_policy.py. 8 CPUs, reserve 1 for OS and 5 GiB RAM; max 6 cores per worker and 6 GiB RAM cap.
- 1 worker 600% CPUQuota; 2 workers 350% each; 3 workers 233%; 4 workers 175%; fifth queued on memory budget. No browser-adjustable quotas, no live systemctl changes in this PR.
- Deployment must connect this calculation to trusted root broker admissions and verified ledger/cgroup identities, rebalance on joins/exits, provide fair FIFO queue and rollback. Never edit transient unit files or risk an active render. Profile already accepts operator flag --worker-cpu-percent; fixed 100% is currently used.

## Early ingest feature flag architecture (separate Engine + Owner work, not implemented)
1. On fully received proxy or video, compute owner-scoped immutable key: owner plus media fingerprint, tool version and proxy schema.
2. Start only media intrinsic tasks (ffprobe, proxy verification and representative frames) in capped per-owner background queue; deduplicate identical input.
3. Keep camera sync, master-specific work, and 360 selected-view analysis project-scoped. Do not let a speculative prewarm write an edit plan.
4. Deleting/replacing a video unqueues and invalidates it; in-flight tasks finish only into unbound cache. On Continue, reuse compatible completed cache, let others continue while UI progresses and maintain exact project ownership.
5. Enforce storage and memory quotas, cancellation/restart safety, versioned cache keys, no cross-owner reads, progress accuracy, and compare timings Drop to first editable frame on real 360 / 4K media.

## Safe deployment after render
1. Confirm actual render children stopped, not merely that resident systemd worker is alive.
2. Stage isolated LAB-JM progress UI and verify WSGI hashes, preserve #402 audio+360; restart portal only when idle. Verify ring plus per-video bars.
3. Review planned fair CPU rebalance and test memory/CPU metrics before activating broker-level capacity policy. A pure allocation function alone is not a running scheduler.
4. Install distinct #405 cross-tab CSRF and #404 unchecked Mixer fixes if approved; browser E2E.
5. Hold early ingest feature until approved Engine/Owner release and E2E. No MAIN/FER, media or current worker changes.
