# MAIN private Music/Session overlay - 20 Nov 2026

Port of reviewed PR #284 Music/Session routes to MAIN at 61a57fd.
Worker, Google Login, Cloudflare, owner database, media and broker do not change.
The LAB-JM Mac installer is explicitly not available in MAIN.

Copy only reviewed root-owned sources into the fixed MAIN-only overlay
and install a reversible MAIN portal systemd drop-in.
The overlay uses the exact pinned full-session.js digest and keeps
unknown session/mix routes denied. Restart only MAIN portal after preflight.
An authenticated real session is required to prove Stage and song review E2E.
