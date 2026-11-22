# JM-approved Mixer and Owner project buttons -> MAIN isolated candidate

This is a **selective overlay integration**, not replacement of MAIN's original Owner/Mixer code. Never copy the LAB-JM Owner overlay onto MAIN: MAIN has independent complex route changes, e.g. 30-song render/recovery, scoped downloads, optimized track names and instrument grouping, protected by SHA-256.

Prerequisites: MAIN backend bundle based on commit `61a57fd9...` with the changed `track_types.py` and `mixer_adapter/single_song.py` plus tests from this promotion branch. Bundle manifest editor_commit must match this promotion branch commit; Engine remains pinned `9af275...`. The MAIN-specific asset overlays have SHA-256 preconditions. The builder takes only the reviewed current MAIN Owner release `/opt/montara-main-release/main-project-name-overlay-20261121` and creates a distinct immutable overlay. It preserves the MAIN `full-session.js`, gateway, Companion and all other app logic, adding voice roles and the confirmed accessible project Open/× controls. It modifies only the UI's voice-group arrays. Existing `sourceLabel()` with cleaning of recorder prefixes and naming remains untouched.

Execution:

```sh
sudo python3 ops/main/jm-approved-promotion/build_overlay.py \
  --target /opt/montara-main-release/main-jm-approved-mixer-<commit> \
  --fragments ops/main/jm-approved-promotion \
  --bundle /opt/montara/bundles/jm-<commit>
```

**Do not** deploy to BETAMAIN (port 8129), FER or LAB-JM. Test the generated MAIN WSGI import and SHA pins before touching systemd. Test backend `tests/test_track_types.py` + `tests/test_mixer_fx_levels.py` against the pinned MAIN runtime. Deploy to isolated MAIN (port 8131) only if no MAIN jobs active, with isolated service overrides and rollback. Verify isolated MAIN portal and broker, endpoints 403/401 for anonymous access, and preserve existing Main song/session and download routes. Browser Owner test must then confirm the Mixer audio and export before any claim of full MAIN production release.

No R2 changes or media deletion. `#379` audio project persistence, `#380` same-slot project upsert, and `#348` ingest-performance are still unfinished and are intentionally **not** promoted.
