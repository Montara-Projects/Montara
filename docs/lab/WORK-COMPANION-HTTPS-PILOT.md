# Work outbound Companion pilot

The isolated test creates an authorized synthetic job, claims it over TLS, invokes the existing VideoJobs renderer, reports progress, submits the MP4 and downloads it using the owner's session. It uses a temporary Flask server with an explicitly trusted test certificate and synthetic application sessions. It does not mount the routes in the public portal.

The Mac explicitly approves a map from remote project IDs to local recipes and folders. No broker-supplied command or filesystem path is executed. The signed finish request binds the payload, lease and operation to the paired device. Publication and state transition occur in the same SQLite transaction. The pilot accepts up to 12 MiB per result and 64 MiB of stored results, with one-hour expiry. Expired results are inaccessible and can be purged by the operator or during upload. A scheduled purge must be wired before publishing.

Before enabling the feature: add an isolated authenticated UI, Keychain registration and rotation, native service supervision and retry behavior, end-to-end cancellation tests, and rate limits. The dedicated route needs an Nginx and portal body budget for the 12 MiB result plus JSON encoding. Never broaden the limits for unrelated routes. Keep the previous portal configuration and turn off the outbound routes on rollback. Revoke pilot devices and preserve real projects.

For larger exports, use resumable direct uploads to private object storage with short-lived capabilities restricted to the job and object, an integrity check on completion, and lifecycle expiry. The broker should handle metadata only. Current pilot cost is bounded to a small temporary SQLite allocation and roughly one outbound download of the MP4 per successful retrieval.

## Isolated browser panel

The pilot blueprint serves the authenticated panel at /urano/v1/companion/panel/index.html when the jobs service is explicitly provided. The panel lists only the signed-in owner's catalog entries, creates a one-time invitation, polls signed presence, creates or cancels a job, polls its progress and links to the authorized result. It makes only same-origin requests. The normal Work application does not yet mount this blueprint.

On macOS, the optional browser smoke test runs Brave with a synthetic Owner cookie and a test-only certificate exception in the isolated browser context. It uses the real button to create the invitation, redeems it using the native client, confirms signed presence, clicks render and downloads the real Engine output. The test verifies all browser requests stayed on the isolated HTTPS origin and checks the result against SHA-256, ffprobe and a complete decode. The test-only credentials and certificate configuration are never copied to an installed browser or public portal.

The existing QA package is unsigned and has no outbound pairing UI. Before publication, wire native onboarding, credential persistence and rotation, add live cancellation and operational cleanup tests, and run a real Google session against an isolated Work instance. Keep the public Work configuration as the rollback target.
