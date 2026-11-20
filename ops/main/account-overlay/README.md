# MAIN account menu + existing Music Session

Restores the previously shipped Work avatar, project dialog, account switch,
language persistence and revocable logout from verified 17 Nov Work history.

Only MAIN Owner portal is updated: no Engine / H4 broker / user media changes.
This is the full reviewed PR #295 Music Session bridge plus account-specific
Google profile, session schema and UI. Previously issued MAIN sessions remain
valid; they have no saved profile. New sign-ins request Google's profile scope.

SessionStore migration adds nullable profile_json and owner language table.
Back up MAIN sessions.sqlite3 using SQLite backup() before activation.
Do not wipe sessions or change owner IDs.

Rollback: restore prior MAIN session overlay drop-in ExecStart/PYTHONPATH,
daemon-reload, restart MAIN portal. Leave broker/worker and media untouched.
