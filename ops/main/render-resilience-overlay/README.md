# MAIN Owner reliable 1–30-song batch render and Mixer audition

Owner-only patches for MAIN tested on a private 15-stem session. Existing
large render fails on WHIB because the old batch started two expensive
full-DSP processes concurrently, then aborted all eight songs if one
failed; no results/ JSON remained and the browser requested 404 for song 3.

This stage reduces >=12-track sessions to one in-process song render at a
time, writes a per-song checkpoint once MP3 and metadata are complete,
preserves completed MP3s across retry using exact SHA of mix/source/window,
and returns status partial with independent failures (rather than
discarding the whole batch). 1–30 songs allowed and explicit Select all /
Clear selection UI, preserving checked selection for the project.

The old listening-range HTTP 500 came from two Flask threads sharing the
same .part.ogg temporary path. Path-keyed thread locks + unique temporary
names prevent concurrent overwrites. Preparing another Mixer excerpt must
never remove completed song result metadata. The new button Choose another
section can sample a different concert offset and restore the saved mix;
Play final mix listens to the full MP3 after that song is rendered.

The reviewed Engine and JM releases stay pinned. New root-owned
sha-pinned worker overlay and reversible MAIN portal 70- systemd drop-in;
old 20/30/40/50/60 layers untouched. Do NOT restart broker or
an unrelated Owner. Owner generation renewal must use verified scoped
ledger and control, *without* DemoBroker.__init__ recovery sweep, which
previously stopped another Owner. No originals or project data deleted.

This PR does not yet expose full-song automatic live processed audio
before rendering, mixer coloration/group/pan or change DSP presets.
Those require separate review and must not be implied to be live.
