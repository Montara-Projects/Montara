# LAB-JM Edit preview, Save Shot and Projects shelf — candidate

Date: 2026-11-23. Stacked on #401/#400/#379. Not shipped to MAIN/FER.

## Reported behavior

1. A long song needs a playable moving preview directly beside the zoomed
   Video Cuts bar. Timeline playhead must track playback and show seconds.
2. Save Shot raises a stale revision after changing a cut and exposes
   a manual reload workflow.
3. New Audio and Video projects appear missing in Your Projects.

## Read-only VM findings

Owner-private workspace: /var/lib/private/montara-h4-jmlab-owner-88be85a4ea8037b8edc43e1166749834d72dcf39

* Seven physically saved video project.json files exist:
  Insel.Gig, Insel.Gig-2 through Insel.Gig-7, including today's edits.
  All seven have the same display name Insel.Gig. No data changed.
* AudioProjects contains only .lock; at inspection no audio-project
  JSON was saved in this owner workspace. Do not claim it was merely hidden.
* Recoverable previous video entries in .ZuckerEditorTrash were not restored.
* First Audio-only save happened after preview buffer decoding + animation,
  even though the mix plan was already available. Partial/incomplete preview
  may therefore prevent initial persistence.
* A roll edit changes the edit-plan revision, while an open Edit dialog can
  still hold the old revision.

## Candidate code changes

- Inside music Edit, use the SAME saved thumbnail motion preview URL in
  a playable video with Play review / Pause, subsecond time readout and
  moving white playhead on the enlarged Video Cuts timeline. The static
  framing picture is hidden while reviewing, with Edit framing to return
  to crop/360 controls. No duplicate frame cards. Bar adjacent to media.
  After roll save, invalidate old preview and use newly refreshed URL.
- One Save shot and local Default. No reload action. A stale revision can
  auto-refresh/retry once ONLY if project, original camera, spherical pose,
  flat framing, movement, playback speed and selected camera all match.
  Concurrent changes to a different shot/camera fail safely; the Engine
  compare-and-swap continues protecting every write.
- Initial Audio-only project JSON save occurs as soon as mix.plan exists,
  BEFORE media buffer download/decode or fader animation.
- Distinguish duplicate names in Your Projects by the actual saved folder
  suffix without renaming any project or project.json.

## Checks and next gate

- Modified JS syntax check PASS; Stage isolation 5/5; preview isolation 4/4;
  Browser bridge and Audio UI PASS; new 6/6 contract tests PASS; 19 focused
  Python project/Stage tests PASS.
- These are NOT authenticated real-browser end-to-end tests. Still verify
  video preview playback, playhead, single Save Shot, persistence of new
  Audio project JSON, and seven distinct video shelf labels.
- Do not restart LAB-JM during live owner editing. Build immutable overlay,
  repin WSGI hashes and QA before activation. MAIN, FER, Engine and 360
  export logic unchanged.
