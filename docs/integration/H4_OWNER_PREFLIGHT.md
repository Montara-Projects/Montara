# H4 isolated Owner startup

Issue #235 describes H4 and the older broker reading different Owner roots.
Keep the existing I26/I27 service and all its data separate.

Use one operator-owned staging configuration for the web UID, GID and
`MONTARA_OWNER_PRIVATE_DIR`. Give the new portal an empty directory owned by
that UID/GID and mode 0700. Map that exact directory into the dedicated broker
unit with systemd `BindReadOnlyPaths=<Owner root>:/run/montara-h4-owner-ro`.
Start the broker with its existing `--h4-native-isolated` option, the staging web
UID/GID, the read-only mount as `--owner-db-root` and the reviewed H4 worker
script and pinned bundles. Keep the H4 socket and ledger separate from I27.
Start the loopback portal only after the dedicated broker is listening.

The portal checks socket ownership, mode and root peer credentials. The broker
verifies the mount is read-only and reports the directory identity to the
authenticated web UID. The portal compares it with its own Owner directory
before opening SQLite. A missing socket or different directory now fails
startup with an explicit diagnostic. The probe does not admit a job or read
session contents.

Before promotion, use fresh staging cookies and two test owners. Verify Google
sign-in, private projects, worker admission, Stage with synthetic media,
saving a take, MP4 and controlled recovery. Verify that neither user can open
the other user's project or media. Roll back by withdrawing only the staging
route and stopping the staging portal and dedicated broker after their jobs
finish. Retain the staging data and leave existing units and routes intact.

## Parallel staging instance

Set `MONTARA_H4_INSTANCE=staging236` for the portal and pass
`--h4-instance=staging236` with `--h4-native-isolated` to the broker. The
instance identifier derives the socket directories, ledger, read-only mount
and worker state names. The portal's `MONTARA_OWNER_PRIVATE_DIR` must be
`/var/lib/montara-h4-staging236-owner`. Bind that exact directory read-only to
`/run/montara-h4-staging236-owner-ro` in the broker unit. Install the reviewed
worker entrypoint and its modules under the root-owned
`/opt/montara/broker-h4-staging236-native` directory. Both services must use the
same instance label, and the named instance must have its own OAuth origin and
client. Leaving the label empty preserves paths and service names from H4.
