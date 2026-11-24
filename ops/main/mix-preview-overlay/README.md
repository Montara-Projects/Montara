# MAIN only: Owner Session WAV preview source validation

Background: public MAIN POST /montara/session/<id>/prepare creates 15
short WAV excerpts under Sessions/<id>/preview/<song>/tracks/.
Its remote-mode POST /montara/mix previously accepted ONLY completed
Uploads, consequently 400-rejecting these verified server-generated files.
The H4 worker bootstrap assigns a secure MONTARA_SESSION_TOKEN at runtime,
so reading /proc/PID/environ does not reveal the secure mode.

Fix in mixer_adapter/source_access.py: only tracks EXACTLY enumerated
in the current session.json for the Owner, session ID, preview_song,
current ready/done state and fixed path shape are allowed. Cross-Owner,
stale, symlink, folder bypass and arbitrary local file requests remain
denied in remote mode. Do not disable MONTARA_SESSION_TOKEN.

Deployed MAIN only: install root-only reviewed source at fixed
/opt/montara/broker-h4-main-native/main-mix-overlay-20261120/mixer_adapter/source_access.py.
Worker-specific verified bootstrap hashes that module and adds it before
original JM imports. No modifications to immutable pinned JM/Engine,
LAB-FER, LAB-JM, Cloudflare, portal, Companion or user media.

New MAIN worker needs a controlled stop/restart via existing Owner broker.
Never force restart live unit from systemctl without ledger/cgroup
reconciliation. Save current session/metadata backup, verify no render,
then use broker Owner-bound stop/start. The browser must refresh to obtain
the new generation. All originals and the current session manifest persist
under the Owner StateDirectory.
