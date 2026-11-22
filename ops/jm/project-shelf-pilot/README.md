# JMLab private Owner project-shelf pilot

Source files are copies of the existing, root-owned JM Owner overlay from 2026-11-22 with an isolated UI change, not replacement MAIN/FER apps.

Baseline JM Owner bridge SHA-256: `1a64fe85e786b18c9f8d77539d6b3cd8a17c255a2db5b96b9e1535ced3a4f500`.

This patch makes each saved project title an accessible Open button, calls the existing owner-scoped `POST /api/v1/wizard/projects/open` using only a server-supplied project path, then retrieves the project snapshot to populate previously uploaded video and audio references before navigating to the existing `?resume=footage` restore path. The × button calls `POST /api/v1/wizard/projects/delete` only after explicit confirmation and passes `keep_exports:true`, with errors surfaced and the row retained on failure. No new Owner or filesystem APIs are introduced.

Requires JMLab Owner's signed-in native bridge and server-side owner verification. If a source is no longer present, opening may fail: do not imply Cloudflare recovery before #371 passes.

Do **not** restart JMLab while upload/render is active. Stage new root-owned overlay, repin the signed `native_owner_browser_surface.py` asset SHA and verified WSGI bridge SHA; preflight before switching systemd. Rollback to the previous systemd portal override without touching projects. MAIN/FER and R2 remain unchanged.
