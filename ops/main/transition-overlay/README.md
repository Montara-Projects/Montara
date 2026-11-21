# MAIN-only non-destructive song transition detection

Fix a real 25+ minute segment in a 106-minute T4T live concert: the old
collective-rest detector requires >=8s of full-band inactivity. For a
continuous set, reviewable RMS instrument transitions in the pinned
existing analysis cache now break suspected 10m+ ranges into probable
3-8m windows, with 10m maximum per proposed cut, subject to listening.
Current 18-interval session replay produces 22 proposals with four new
transition candidates; original source files and existing saved mixes are
not touched.

**Existing session repair**: POST /montara/session/{id}/suggest (same Owner
CSRF, 12-digit valid session ID and generation). It reads ONLY the
server-owned NPZ cache with allow_pickle=False and size limits, accepts
current candidate songs and returns proposed windows **without writing**.
Authenticated Music review screen offers "Improve song boundaries" to
request proposals; changes appear locally for listening and only selected
windows are saved by existing /songs. Existing unchanged windows retain
their own mixer settings, split windows require new mix decisions.

**New session detection**: enhanced mixer_adapter.session detector is loaded
in a reviewed root-owned MAIN-only worker overlay and inherited via verified
PYTHONPATH by its sandboxed child processes. The verified JM/Engine commits
remain pinned. No change to signed recorder files or LAB-JM/FER.

The old MAIN portal 20/30/40 layers remain; add a reversible 50- drop-in
for this overlay. The worker module overlay requires a controlled broker
stop/start of Owner generation 20 after no current render/encode jobs and
with session metadata backed up; never directly restart or mutate another
Owner's unit. Ensure root-only SHA pin for backend worker modules, and
that current worker #298 source-access patch stays intact.

No automated split is certified as a song ending. The user must listen at
candidate boundaries; real long medleys can be restored by merging/review.
