# MAIN Save Mix -> full-song preview -> render: consistent per-song settings

Private Owner MAIN only, no changes to LAB-JM/FER or global pinned Engine/JM.
Distinct SHA-pinned worker modules and Owner-authenticated portal overlay.

- Save in Mixer persists user-chosen voice/bass/drum levels, full audible
  automatic gain baseline, mutes, per-channel pan, EQ and explicit FX
  ON/OFF in the private session manifest.
- Song-list Play after Save never loads the rough equal-level guide.
  It renders the FULL song using the same SingleSongMix and vendor DSP
  as the final export; user sees preparing until audio is ready.
- Audio is cached by source/window/role/settings SHA in per-Owner
  mix-previews/song/SHA, never plays stale user edits.
- Export uses original ranges; prelisten uses existing Opus proxies until
  originals arrive. Source fidelity may differ despite same DSP settings.
- Manual pan [-1,1] in WebAudio and vendor render; old automatic role
  pan is restored when manually overridden render exits.
- Reversible private portal 90- drop-in and owner-specific worker restart
  only when idle, without invoking DemoBroker constructor.

## Required modules for isolated subprocesses

The MAIN worker launches per-song subprocesses with Python `-P` so the
pinned JM working directory cannot shadow the verified MAIN audio module.
The worker overlay **must include the entire adapter dependency set**:
`mixer_adapter/session.py`, `single_song.py`, `extract.py`,
`render_progress.py`, and the verified MAIN `source_access.py`.
The two supporting extraction/progress files are byte-identical to the
pinned JM bundle; source_access is copied from the already-reviewed
MAIN source-access overlay. Keep everything root-owned and readonly.

A missing support module previously caused infinite retries during Play
after Save mix. Confirm the child import contract with `python -P`
and the actual worker PYTHONPATH before deployment, then confirm a
real saved-song preview is generated. Merely checking the portal status
does not verify the full audio processing path.
