# MAIN Mixer instrument identity, channel order and group colors

Reviewed MAIN-only Owner web surface override for three exact static assets:
montara.js, track-types.js and montara.css with immutable root-owned
SHA pins. Original upload filenames and track keys do not change.

Drum channels ordered Kick, Snare, Hi-hat, Toms, Overheads;
then Bass, Guitars, Piano/Keys, Synth and other instruments;
vocal mics last. Visible short labels, instrument family colors, reversible
Drums/Voices/Stereo L/R group buttons; linked fader delta/Mute/Solo
preserve individual offsets and all source files. The recorder event suffix
is removed ONLY from display labels; chosen manual type wins.

New worker-only checked overlay adds track_types.py to prior ROOT verified
MAIN audio modules. For historic review sessions where type='other' and
chosen=false, infer the instrument from structured recorder stems on the
fly so the existing per-instrument EQ, compressor, dynamics, level and pan
dictionary is actually used on the final render. Explicit chosen=true
types are never overwritten. Original manifest remains untouched.

Needs scoped worker generation renewal only when no render active. A
separate reversible MAIN portal 80- drop-in activates the new WSGI static
asset source; previous 20–70 drop-ins remain; no LAB-JM/FER changes.
No general manual pan feature or instant full-song DSP preview is claimed
by this PR: both require separate source/preview DSP contracts and tests.
