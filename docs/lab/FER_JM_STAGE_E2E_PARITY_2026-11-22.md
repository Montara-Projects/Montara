# FER ↔ JM Stage E2E parity and stability gate — 22 Nov 2026

**Status:** read-only baseline and diagnostic harness. No change to Engine, frontend
runtime, Cloudflare, Companion, owner sessions or media. Coordinates #359 with
existing #358, #356, #348, #265 and FER proof PRs #242/#250.

## What passed historically versus what remains unproven

| Component / journey | FER E2E on Windows 10, 16–17 Nov | JM current, 22 Nov | Transfer |
| --- | --- | --- | --- |
| Google private Owner and Cloudflare HTTPS | Human pass at LAB-FER origin | Isolated LAB-JM portal active, session-specific E2E still needed | Reuse architectural contract, not OAuth cookies, secrets or site URL |
| Companion | Windows .NET/PyInstaller, 127.0.0.1:47820, exact FER CORS #249 | macOS Companion 0.6.14, exact JM origin + per-site LNA permission | Reuse HTTP contract and allowlist tests, not binaries |
| Source upload, proxies, sync | One human pass: proxies and MP3 (not original), selected song | IngestStage #348 slow with several cameras / 360 | Preserve source identity; compare source sizes and workflow |
| Frame review and shot edit | Human pass with ~120 shots; first Save reloads thumbnails | 305-shot project; Save 409, edits up to 37.74 s | Reuse regression #243/#253, not claim performance parity |
| Hover media | Used in old FER workflow, no 305-shot pass | GET preview synchronously renders when cache missing; observed up to 42.37 s | Needs bounded async render/status + cache/priority |
| Final MP4 | Download of low-res-proxy-based test MP4 reported | No equivalent full current JM acceptance | Verify decoded video and audio, quality and destination |
| 360 and green frame artifacts | No FER E2E pass recorded for current 360 + macOS combination | 360 route #356, green glitch report not yet independently reproduced | Test codecs/360; no unsupported claim of parity |
| Engine pin | Historical b867b3c... | 9af275b... | Never blindly copy old FER Engine into JM |

FER baseline is in docs/lab/LAB_FER_STAGE_WINDOWS_E2E_BASELINE_2026-11-17.md
and docs/integration/I5B_STAGE_VIDEO_WINDOWS_E2E_CHEMA_HANDOFF_2026-11-16.md.
The FER E2E did NOT certify original-quality final export, current macOS, or the
complete modern feature matrix.

## Observed JM route latencies (real worker logs, 45-min inspection)

Created by scripts/diagnostics/owner_route_latency.py; *slow-log samples* are
thresholded by the running worker. Their median/p95 are conditional on having
been logged, NOT all-requests or browser/Cloudflare E2E latency estimates.

| Route | Access count from sample | Slow-only sample count | Slow-only median | Slow-only max |
| --- | ---: | ---: | ---: | ---: |
| GET review?render=0 | 197 HTTP 200 | 197 | 5,990.6 ms | 142,197.1 ms |
| GET review preview/:shot | 20 HTTP 200 | 20 | 14,970.5 ms | 42,366.6 ms |
| GET edit/shot/frame | 2 HTTP 200 | 2 | 40,380.6 ms | 46,337 ms |
| GET edit/shot | 4 HTTP 200 | 4 | 6,601.8 ms | 12,356.1 ms |
| PATCH edit/shot | at least 1 HTTP 200 | 2 slow samples incl. 409 | 20,391.2 ms | 37,742.6 ms |

Live journal shows 5.5–6.2s review calls even with no FFmpeg process active.
Source: engine/server/api.py GET /api/v1/wizard/review calls
core.shot_review.review_items() for EVERY status request, and
GET /api/v1/wizard/review/preview/:shot synchronously invokes
review_previews.render_preview() on a cold clip, so the browser blocks while
FFmpeg is generating a video. The latter route is an architectural priority.

**Falsified hypothesis:** 310 saved review-candidate summaries occupy ~15.15 MB,
but reading/parsing/counting them took only 0.10–0.16s in a separate read-only
microbenchmark. They are NOT sufficient to explain the six-second review response.
Profile the remaining path (segments, coverage, per-shot path probes, preview
identity, lock contention and serialization) before optimizing or adding caching.

The latest JM portal includes #358's bounded polling/hover dwell mitigation. It
does NOT fix the slow Engine routes. Timeout increases can prevent misleading
503s but do NOT make the backend faster, and may approach Cloudflare limits.

## Non-invasive, privacy-preserving log diagnostic

Run locally or on the authorised VM; do not upload raw logs:

    sudo journalctl -u <JM-WORKER-UNIT> --since "45 minutes ago" -o cat \
      | python3 scripts/diagnostics/owner_route_latency.py --label JM

For FER, supply its own **actual** worker journal and --label FER; empty results
mean instrumentation unavailable, NOT faster FER. The tool emits aggregate
allowlisted route names, status counts and conditional slow-sample latency.
All paths, filenames, query parameters, cookies and project identifiers are
discarded. It does not create new infrastructure, read media or time real
Cloudflare end-to-end latency. To measure actual user experience, instrument
request IDs and monotonic browser→Owner→broker→Engine→media→UI spans separately.

## Stage parity release gate (no false PASS)

1. Fixed reference with authorised access (#332) and a real 300+ shot project.
   Record Engine/portal/Companion SHAs, hardware, codec/projection/360, cold/warm
   cache. Reuse existing fixture only after actual publication/consent.
2. Browser-through-Cloudflare with real Companion: login, ingest from ≥2
   cameras and master, 360 and a short optional insert, sync, timeline, first
   Edit, second Edit, Save, Swap, hover cold and warm, project resume, final
   render and decoded playable MP4 with correct audio.
3. Error classification: 401/403 permission, 404 routing, 409 true revision or
   busy, 503 network/proxy timeout, 500 backend. Do not auto-replay stale
   state-changing edits. Retry only safe/idempotent calls, with request IDs.
4. Performance: measure click acknowledgment (<100ms target), warm Edit
   (<500ms target), uncached hover asynchronous with immediate still image and
   bounded queue, snapshot review status cheap, no 90s synchronous Swap.
   Report actual values and failures; do not mistake a spinner for speed.
5. Green/visual artifacts: capture privately approved short sample; compare
   original, proxy, 360 projection/frame, FFmpeg decoder errors, selected codec,
   color space and output. Verify visually; do not presume GPU or disable safety.
6. All HTTP routes exercised via same frontend contract, no missing review
   previews or accidental upload of original, secure Owner/CSRF, exact CORS and
   Chrome LNA grant. Replay once after a controlled restart/recovery.
7. Preserve FER and MAIN. Only staged JM changes with rollback and validated
   idle gate. Require both FER review and real JM human E2E before promotion.

### Ownership and non-duplication

Joint gate #359; real 305-shot interactive latency #358; 360/review #356;
ingest #348; FER benchmark #265; LAB-FER Windows evidence PRs #242/#250;
CORS/LNA #249/#339/#319; research #321. FER supplies previously proven
contracts and executable reference, JM maps deployed differences and supplies
read-only measurements, both validate staged changes. No fresh VM or portal.
