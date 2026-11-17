# Work outbound Companion pilot

The isolated test creates an authorized synthetic job, claims it over TLS, invokes the existing VideoJobs renderer, reports progress, submits the MP4 and downloads it using the owner's session. It uses a temporary Flask server with an explicitly trusted test certificate and synthetic application sessions. It does not mount the routes in the public portal.

The Mac explicitly approves a map from remote project IDs to local recipes and folders. No broker-supplied command or filesystem path is executed. The signed finish request binds the payload, lease and operation to the paired device. Publication and state transition occur in the same SQLite transaction. The pilot accepts up to 12 MiB per result and 64 MiB of stored results, with one-hour expiry. Expired results are inaccessible and can be purged by the operator or during upload. A scheduled purge must be wired before publishing.

Before enabling the feature: add an isolated authenticated UI, Keychain registration and rotation, native service supervision and retry behavior, end-to-end cancellation tests, and rate limits. The dedicated route needs an Nginx and portal body budget for the 12 MiB result plus JSON encoding. Never broaden the limits for unrelated routes. Keep the previous portal configuration and turn off the outbound routes on rollback. Revoke pilot devices and preserve real projects.

For larger exports, use resumable direct uploads to private object storage with short-lived capabilities restricted to the job and object, an integrity check on completion, and lifecycle expiry. The broker should handle metadata only. Current pilot cost is bounded to a small temporary SQLite allocation and roughly one outbound download of the MP4 per successful retrieval.
