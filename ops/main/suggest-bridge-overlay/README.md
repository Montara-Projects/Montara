# MAIN Owner /suggest browser allowlist (20 Nov 2026)

The real MAIN worker and Flask API already support POST
/montara/session/<12-hex>/suggest. The full-session review UI called it,
but owner-bridge.js returned "Original Montara operation not enabled in
this private beta" before sending any request. This narrowly adds
"suggest" to the existing Owner-specific authenticated POST/no-query
allowlist. No new arbitrary endpoints, HTTP methods, or query parameters.

The browser bridge is rooted in the private Owner portal overlay, served
only after Google session verification. Root-owned SHA256 pinned.
New layered portal drop-in 60-main-suggest-bridge-20261120.conf resets
only portal ExecStart to the corresponding reviewed WSGI factory and
its PYTHONPATH; prior 20/30/40/50 layers remain in place.

Backend/API/worker session files, saved 15 WAV originals, Mixer,
Companion, project workspaces and LAB-JM/FER stay unchanged. Rollback
remove only the 60-main-suggest-bridge-20261120.conf drop-in, run
daemon-reload, restart MAIN portal only.

Tests include Node bridge authenticated POST /suggest and denials for
GET, injected query strings and invalid session IDs, plus Python
server-side route allowlist. Existing full-session.js SHA remains pinned.
