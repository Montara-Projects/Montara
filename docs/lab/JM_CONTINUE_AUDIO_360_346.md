# LAB-JM: After Continue, camera-audio preview and registered 360 source frame

Issue: https://github.com/Montara-Projects/Montara/issues/346

This is a **candidate patch** in a reviewed branch, not a production release. Deploy to JM only, never MAIN/FER by default.

## Symptoms and intended changes

- After Continue, a video-only project has no Master/Songs track. The old openSongRange function hid its song-range player, even if an imported camera proxy contains playable AAC.
- The 360 panorama uses the precise GET /api/v1/wizard/spherical-source-frame?source=... endpoint. The authenticated Owner browser bridge and Stage route validator denied it, so the view selector stayed loading.
- Change 1: allow exactly this one read-only JPEG request, only for structurally valid Montara private Owner Uploads media, with one bounded source parameter. Reject methods other than GET, duplicate parameters, other directories, malformed paths, and arbitrary endpoints.
- Change 2: select the already downloaded Companion small MP4 video File for **camera-audio audition** when there are no independent Master/Songs tracks. Use a browser blob URL; don't upload audio again, extract an audio file, or silently set an audio master. Keep 256 MiB max per proxy, 384 MiB max retained across candidates; revoke blob URLs on remove/reset. This is browser-session-only, not persisted across reloads.
- The Engine handler already uses the current project and checks the resolved source against the project's enrolled video paths; returning 404 for a nonmember. We retain this boundary. The gateway still checks authenticated Owner, CSRF and Engine generation, and restricts review-media response MIME and bytes.

## Test evidence

Local macOS:
- node --check of web/montara.js and native_owner_browser_bridge.js: PASS.
- python -m unittest tests.test_jm_346_spherical_route: 3 PASS.
- node tests/test_native_owner_browser_bridge.cjs: PASS, including an authenticated successful spherical JPEG and blocked GET variants, POST, duplicate query, and disallowed paths.
- node tests/test_jm_346_camera_audio_preview.cjs: PASS, confirming fallback isolation, memory cap and reset code.
- Python pytest of stage-route and browser surface: 7 PASS and 25 subtests PASS.
- Integration suite tests/test_native_owner_h3_authenticated_gateway.py **NOT verified on macOS**: first AF_UNIX path-length failure with default temp; with TMPDIR=/tmp the next failure is missing Linux-specific socket.SO_PEERCRED on macOS. Run this suite on Linux before release. Do not call this a functional E2E test.
- No authenticated Brave playback, no video export and no live 360 preview verification have been performed for this patch.

## Mandatory JM-only deployment gates (not executed by this PR)

1. Verify there are no active browser imports, resumable uploads, FFmpeg, video proxy conversion, render jobs or other task mutations; Companion health must not be busy. An old process existing is not proof of an active render; check real logs, status and recent writes. If uncertain, do not deploy.
2. Verify the service's **current** JM overlay and its authenticated WSGI preflight. The Git base is an older, reviewable source; do NOT replace the live JM overlay with this old branch wholesale, because later fixes for branding/recovery/selected cameras are already deployed in JM.
3. Before applying changes, run Linux H3 socket/CSRF tests and Owner security regression; confirm project-specific source path matches private Uploads and current worker's registered video list. Re-audit owner directory permissions, symlinks, response MIME, and 403/404 for other owner/project.
4. Build a fresh root-owned, immutable JM overlay by surgically applying these three source diffs onto the **current** live JM files. Generate reviewed SHA-256 pins for browser bridge, Stage-route-related assets and injected JS, and update the trusted WSGI preflight. NEVER disable digest checks, widen generic routing or skip an import failure for deployment. Record before/after SHA and nonsecret manifest.
5. Save and verify a root-only rollback copy of portal unit/drop-ins/current overlay configuration. Start with WSGI import preflight as the service UID, JS syntax and systemd-analyze verify. Restart **JM portal only** in an idle window, not its Engine jobs or broker. Leave MAIN and FER untouched.
6. Perform **human** JM E2E with the existing recovered C0020 camera and one registered 360 camera: click Continue, play/pause audible camera proxy, load panorama, choose/rename viewpoints, persist them, export a short project, and confirm no camera audio was misclassified as Master. Check separate Master/Songs playback still works and logo/other JM features have not regressed.
7. Roll back the JM portal on any 401/403 unexpected error, SHA mismatch, lost session/project or broken playback. Keep issue open until human acceptance.

## Known limitation

The optional camera audition uses only in-memory proxies from the **current** import, not past saved/reopened project media. If there is no cached playable camera MP4, the existing UI remains hidden rather than guessing a master or copying original 360 files. Huge proxies exceeding the memory budget are skipped. This is explicit, not silently claimed to support every camera file.

## Protected resources

Original camera videos, MP3 Masters, existing JM sessions, Companion cache, Cloudflare tunnel, MAIN Owner data, LAB-FER files and R2 configuration are outside this change. The branch is draft and cannot be deployed merely by merging it.
