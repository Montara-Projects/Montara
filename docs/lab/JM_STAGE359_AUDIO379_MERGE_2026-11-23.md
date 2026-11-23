# Stage #359 on approved Audio #379 — integration record, 2026-11-23

**Lab only. Do not deploy these paths to MAIN, FER or shared Engine. Swap is explicitly excluded.**

## Exact sources

- Current, human-approved LAB-JM Audio #379 overlay: `/opt/montara/jmlab-audio-projects-379-verified-20261123`.
- Corresponding approved backend bundle: `/opt/montara/bundles/jm-736eee61b1ebdd89910642462ed371c04445275e`.
- Base for three-way comparison: `/opt/montara/jmlab-mixer-label-hotfix-20261122`.
- Previously reviewed but **not previously deployable over #379** Stage candidate: `/opt/montara/jmlab-stage359-pr361-378-candidate-20261122` (PR #383; stacked #378/#361).
- New overlay built **without overwriting any source**: `/opt/montara/jmlab-stage359-on-audio379-candidate-20261123`.
- GitHub reproducible builder: `ops/jm/stage359-on-audio379/build_overlay.py`. It is reference tooling, does not touch running services.

## Scope and preservation

Three-way merge (0 conflicts) of Stage+Audio for `web/montara.js`, `urano/native_owner_browser_bridge.js`, `urano/native_owner_web_gateway.py`; copied the reviewed `web/cut-editor.js`; manually reconciled *only* the `web/montara.js` digest conflict and `cut-editor.js` asset entry in `urano/native_owner_browser_surface.py`. Reviewed WSGI preflight and manifest SHA values updated.

SHA-256 of resulting files:
- `web/montara.js`: `0b06860acd13fad3a0a9bbbc56759c8a74845a29a19017403b0a51455b1d1695`.
- `urano/native_owner_browser_bridge.js`: `196f163a39e41ac47b75693dab2067426994d06558cad7e1ee1b831097d46366`.
- `urano/native_owner_web_gateway.py`: `b61dca5d66f7987e68ac8fb10accab6bd66a9c2a6549baeb9486f4c9a0acfe50`.
- `urano/native_owner_browser_surface.py`: `91bc028fe83694f04c6ae73218f39243c7381852c8de6a57c7bd5ed2ce914639`.
- `web/cut-editor.js`: `ba000bfa984aa54fc26b8c3117aba503cc2b0bdfc8a9759d41a7322f13de3e70`.

Preserved SHA-identical from approved #379: `web/full-session.js`, `urano/native_owner_mix_http.py`, `urano/native_owner_full_session_http.py`, `urano/native_owner_app.py`, `urano/owner_account.css`, `web/track-types.js`, `web/montara.css`. Static markers `/montara/mix/projects`, `audioProject`, `queueAudioSave`, and `montara-open-edit` remain present after merge.

## Checks and activation

- Manifest digest verification **14/14 PASS**.
- Import/preflight as restricted `montara-jmlab` portal user with exact overlay+bundle `PYTHONPATH` **PASS**.
- Node syntax of `web/montara.js`, `web/cut-editor.js`, Owner browser bridge **PASS**.
- Python AST for WSGI, gateway, browser surface **PASS**.
- Zero running JM Owner jobs at pre-deploy check.
- One new isolated systemd drop-in: `/etc/systemd/system/montara-h4-jmlab-portal.service.d/zzz-jm-stage359-audio379-20261123.conf`, selects only new overlay `PYTHONPATH` while preserving the approved `jm-736eee61...` bundle.
- **Only LAB-JM portal restarted.** After restart portal active (PID 182870), JM broker unchanged and active (PID 180955), no running JM jobs, anonymous local HTTP routes return 403, expected for protected Owner surface.
- **No** MAIN, FER, Engine, Mixer, broker, user media, database, project or Cloudflare modifications.

## Unresolved / no overclaim

This changes Owner/UI handling of Save conflict, preview 202 safety, partial review and gateway timing/status hints. **It does not install asynchronous Engine PR #78**, because `abd9866` is not proven compatible with Engine pin `9af275b` and Stage/360/Mixer/export modifications. Therefore no claim that cold preview or Swap became faster, or that real 305-shot #359 E2E is complete. Need human authenticated regression #379 and Stage Edit/Save/preview; capture actual latencies. Swap async idempotent queue remains separately pending.

Rollback if user-visible regression: verify idle JM jobs, remove **only** the new `zzz-jm-stage359-audio379-20261123.conf`, `daemon-reload`, confirm prior `PYTHONPATH` restored to `jmlab-audio-projects-379-verified-20261123`, restart **only JM portal**, verify original Audio Save/Reopen. Do not delete any project data.
