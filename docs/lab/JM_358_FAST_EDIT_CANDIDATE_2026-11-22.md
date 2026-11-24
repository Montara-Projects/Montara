# JM #358 — fast edit candidate: Save, hover, scoped review

**Candidate only; NOT deployed.** Linked to P0 #359, FER #265 and Engine PR
https://github.com/amehcgracia-byte/zucker_videos/pull/78.

## 1. Save and 409

Immediate Saving feedback, preserved Engine status and code, separate busy and
stale revision 409 messages. The form retains every changed field. An explicit
Reload latest shot action retrieves the current document and maps the candidate
camera by source identity and label, not list position. It restores the draft,
but NEVER replays the save automatically. If the source view disappeared, show
the draft and prevent accidental saving to a different camera until the user
selects one. Owner CSRF/generation and Engine revision guards remain intact.

## 2. Preview hover

Engine queue has one FFmpeg producer, bounded to 3 outstanding jobs, single
flight per shot/source/pose/audio cache identity. Uncached preview GET responds
202 JSON immediately, original range-capable path streams MP4 once ready.
Private Owner bridge retries 202 under the same CSRF/generation verification,
only attaches valid MP4 as browser-local blob, and cancels abandoned hover.
Native Engine app polls 202. On projects >100 shots, eager video-prefetch is
disabled but photos remain preloaded and explicit shot prefetch remains enabled.

## 3. 305-shot review

A read-only whole-review status snapshot is cached under persisted input file
mtimes and thumbnail/preview/status publication directory mtimes. Plan change,
project change or new media invalidates it. Shot-scoped review requests only
build and return one item's metadata, with partial:true; the browser updates
that one card without deleting other cards or altering global loading counts.
Single-shot Stage hover does not assemble all 305 segment states.

## Verified tests

- Engine at abd98667: 28 backend tests PASS, including actual FFmpeg preview
  and isolated camera editing, 305-shot selective metadata, error singleflight,
  cache invalidation, and no eager 305-video background queue.
- Owner browser bridge: 202 to 200 verified with private CSRF and blob;
  Save stale/busy 409 with no replay and draft recovery; scoped 305 DOM update.
- Stage isolation: 4 JS tests PASS.
- Native Owner workspace and surface: 10 Python tests and 12 subtests PASS.
  macOS strict project-path tests require TMPDIR=/private/tmp because the
  default /var/folders symlink is an unrelated fixture issue.

## NOT yet validated or deployed

There is NO live authenticated Cloudflare E2E on JM's 305-shot project and no
new real user latency benchmark. Immediate click feedback is not a promise
that an Engine save finishes under 500ms. 503 under load, green artifacts and
full original-quality export are NOT confirmed resolved.

LAB-JM currently runs a later, root-owned UI-performance/360/review-controls
overlay not present in main. A deployment requires a three-way merge of exact
live assets, new WSGI/Owner browser-surface SHA pins, service-UID QA, idle
gates, a rollback, and real browser E2E. Never overwrite FER or MAIN or restart
while media jobs are running.

Manual acceptance: same project, 305 Frames, cold/warm hover 202 to MP4
without 503, Edit/Save/Swap, stale 409 draft recovery, 360, per-shot change
without rekeying other cards, restart/resume, original MP4 and master audio.
Report measured click-to-feedback and worker/proxy latency. FER review requested.
