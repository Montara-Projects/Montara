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
