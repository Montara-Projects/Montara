# Vercel and Compute Engine staging

The existing montara-tau.vercel.app alias is production. Use a separate Vercel
preview to test the interface. The Google VM has a reserved external address
and a separate H4 staging broker. Publish a backend hostname owned by the
operator, with a valid certificate and an isolated Nginx server block. Use
the template in deploy/staging/nginx.conf.in and keep the portal on loopback
8127. Leave 8126 and the existing routes alone until the new path is verified.

Current Owner login binds its cookies and CSRF to the exact HTTPS origin.
The browser bridge uses same-origin credentials across fetch, XHR and media
URLs. A Vercel-generated hostname and a separate backend site cannot safely
reuse this browser contract by just adding CORS. For initial verified Owner
acceptance use a top-level backend editor navigation. Before moving the editor
itself to Vercel, choose frontend and API subdomains under the same site, and
test credentialed requests, exact origin checks, OAuth redirects, media
ranges, downloads, Companion and browsers with third-party cookies disabled.
Do not broaden cookie domain or trust arbitrary forwarded headers.

Register https://<backend hostname>/urano/v1/google/callback on the dedicated
staging OAuth client only. Install its secret as an owner-readable private
file outside the checkout. Verify no unauthenticated project access before
opening staging to test owners.

Use the existing resumable upload endpoints and authoritative offsets. Chunk
requests must go from the browser to Nginx and the owner worker, without a
Vercel Function or request-body buffering in Nginx. The currently reviewed
bundle allows 2048 MiB for proxies and 256 MiB for originals. A 20 GB file
requires a separately versioned, inspected staging upload profile and enough
disk for processing and concurrent uploads. Do not advertise 20 GB until
allocation, resumption, one-copy persistence and export have been measured.

Rollback by withdrawing only the staging frontend link and backend route,
then draining and stopping the staging portal and broker. Keep the staging
data and the original status page. No changes to JM, Main or old H4.
