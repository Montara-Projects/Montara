# Mixer: multiple vocalists and instrument preset audit

**DRAFT SPECIFICATION ONLY — not implemented.** Tracks issue #350; coordinate with #313 (instrument EQ, dynamics and pan), #311 (instrument labels), #111 (stereo L/R) and #317 (human accepted Mixer baseline). Do not deploy or merge expecting new Mixer features.

## Target behavior

Montara already labels tracks vocal or backing_vocal from names. A name does not establish which of multiple simultaneous singers leads the song. Support two, three, four, five or more singers with clear lead voice, backing vocals, harmonies, duets, co-leads and soloist changes by song section. Preserve all voices; do not wrongly discard quiet harmonies.

## Identification contract

- Independent vocal stems/microphones are analyzed by track and musical section. Count vocal tracks separately from unique singers; a single stereo camera mix cannot reliably reveal five independent human voices or provide five separated stems.
- Propose role per song/section: lead, co_lead, backing, choir or unknown; include confidence and evidence type. Multiple co-leads and all-choir arrangements are valid, with no imaginary lead.
- Consider VAD/activity, phrase lead, harmonic relationships, timing, intelligibility and cross-mic correlation/bleed, not simply the loudest track. Require conservative uncertainty when identity or lead is ambiguous.
- User may set or lock a role, correct it per section and audition before/after. AUTO must never override manual role locks or silence an unrecognized voice. Changes persist through Save Mix, playback, final MP3 and song changes.
- Role/timeline decisions must affect rendering and cache keys, and maintain existing pan, stereo pairs, EQ/FX controls and verified saved mix behavior.

## Audit actual per-instrument DSP settings before changing presets

For each role (lead, coros, kick, snare, HH, overheads, other drums, bass, guitars, keys/synth, brass, strings, percussion, room) document actual live algorithm, version, defaults, bounds and tests for:
- Source role and routing, gain, fader, auto-level, LUFS, headroom, limiting and true peak.
- HPF/LPF, parametric EQ frequency/gain/Q, compression threshold/ratio/attack/release/knee, gate/expander and de-esser if present.
- Panning/stereo width, correlation/phase, linked stereo pairs, reverb/delay/FX and wet/dry, ducking if present.
- Real preview vs Save Mix vs full-song export parity; preserve manual settings, no clipping, no false instrument assumptions.

Do not invent parameters not found in deployed code. Coordinate with #313, rather than repeating its preset or manual-pan work.

## Required test matrix

1. Two vocal mics: clear lead plus backing, both audible.
2. Five vocal mics: one lead + four backing, all five retained without excessive sum.
3. Two alternating soloists, and simultaneous co-lead duet: no fixed global assumption.
4. Unison/choir with no leader: never invent lead.
5. Doubled same singer and shared bleed: do not count independent singers from track count or loudness.
6. One stereo mixed video: unknown speakers, no artificial separation claimed.
7. Corrupted/quiet/ambiguous stems: preserved and flagged, no destructive role changes.
8. User fixes role manually; persist to new project opening, saved full song, preview and downloaded MP3.
9. Check actual levels, phase, stereo image, LUFS/true peak, clipping and vocal intelligibility with user A/B listening on real songs.
10. No change to 360, Sync, session recovery, instrument role selection or current mixer parity.

## Deferred delivery

First inventory actual presets and representative real multivocal session; design explainable model + confidence with manual overrides; then implement DSP/UI, tests and opt-in rollout separately after user review. Estimate GPU/compute only if source separation is shown to be needed, effective and costed.

**This PR changes documentation only; it is a future fix specification, not a functional release.**
