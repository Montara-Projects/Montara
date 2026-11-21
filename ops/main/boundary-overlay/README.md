# MAIN-only explicit review of long detected song windows

User's 106-minute MAIN session detected 18 proposed songs using collective
instrument rests. Four intervals exceed eight minutes (notably Song 02 at
26m17.5s); two songs can be joined by continuous stage sound. Do not
invent splits or modify originals.

This updates only the original full-session.js Owner review surface:
- identify selected songs >=480 seconds before exporting;
- ask a direct native confirmation, before sending any uploads or changing
  render state; cancellation keeps work/results untouched;
- allow Split at explicit **concert** mm:ss/hh:mm:ss, not blindly at midpoint;
- preserve existing preview + song-specific Mixer / account / video flow.

The worker-side full_session.py guard is also included in this PR, with
tests, but activating it requires a separately vetted MAIN worker change.
Do not hotpatch the immutable JM bundle or restart active Owner jobs while
they are using the Mixer. Until that is deployed, the browser confirms
long song windows but unauthenticated/public requests remain prohibited
as before.

Safe rollout: new root-owned verified portal overlay at
/opt/montara-main-release/main-boundary-overlay-20261120 with exactly
the previous MAIN account + Music sources, except this JS and its
hardcoded SHA check. Activate only a reversible MAIN portal drop-in
40-main-boundaries-20261120.conf; the broker, both Owner workers,
users, uploads, sessions and LAB-FER/JM are never modified.

Rollback: remove ONLY the 40- drop-in, daemon-reload and restart
MAIN portal, keeping the prior 20-/30- layers. Original 15 WAV files,
reviewed 18 cuts and already mixed MP3 remain available.
