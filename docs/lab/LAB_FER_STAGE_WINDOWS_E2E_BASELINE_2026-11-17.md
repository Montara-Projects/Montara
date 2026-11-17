# LAB-FER — Stage Windows / Companion E2E baseline and handoff (2026-11-17)

## Scope and acceptance

Private, **isolated** FER-only browser endpoint: `https://montara-lab-fer.memoriainvalida001.workers.dev`.

Fernando completed a **human E2E** on Windows 10: Google OAuth → new Stage project → Windows Companion I5b local service → camera video proxy upload (**not original**) and MP3 → Continue / local project directory → Start here / End here → sync → Frames and shot edit → local Companion render → MP4 file downloaded with the name chosen in the editor. Download used `http://127.0.0.1:47820/video-renders/{render-id}/file?download=1` and saved to browser Downloads; automatic output to project folder remains **unimplemented**. The editor warned that the **test final video was built from the smaller versions**. **Do not claim original-quality final export**, Mac QA, production installer signing or auto-update success.

Browser test issues: first `Save shot` visibly refreshes whole thumbnail grid, **observed with both 23 and ~120 shots**; second `Save shot` refreshes only edited shot. Merely opening `Edit` no longer reproduces. UI incorrectly says `Mac` on Windows. The problem is **not explained solely by number of shots**: isolated synthetic 3- and 125-shot Playwright tests passed, but do not reproduce the real first-save issue.

## Exact baseline, retain these pins until intentional change

| Item | Baseline / location |
| --- | --- |
| GitHub repository | `amehcgracia-byte/Montara`, main at original private FER deployment `457eebfc1bfed2895fda4be79f635953d56d79ea` (not necessarily current main) |
| LAB-FER Worker | `montara-lab-fer` on Cloudflare Workers |
| Private VPC Service | `montara-lab-fer-private-8126`, ID `01a1e6fe-ff46-7a12-8d86-a6923a763d45` |
| Tunnel | existing `montara-owner-fg`, ID `4a65ebdb-268e-4879-9d99-db1ec05c4041` |
| VM portal user unit | `montara-lab-fer-portal.service`, loopback `127.0.0.1:8126` |
| VM root broker unit | `montara-h4-fertrial-broker.service` |
| FER private owner data | `/var/lib/montara-h4-fertrial-owner` |
| FER broker state | `/var/lib/montara-h4-fertrial-broker/jobs.sqlite3` |
| FER broker source | `/opt/montara/broker-h4-fertrial-native` |
| Companion service engine | `b867b3c72af8fe4685b487bcf1e09ffcc2a7c82b` |
| Companion Python service | reports `0.6.10`; native Windows QA UI `0.6.12.0` |
| Windows QA working copy | `%USERPROFILE%\Desktop\Montara-I5b-QA` (local, **not** versioned deployment) |
| Windows service | `127.0.0.1:47820`; launcher `companion/windows_native/BundledService.cs` |
| CORS fix | GitHub PR #249, exact LAB-FER origin only; locally compiled/restarted on Windows during E2E |
| Thumbnail regression test | GitHub PR #243, test extension catches image refetch after first save; human bug still unproven in synthetic fixture |

Do not treat a local QA build as a signed or distributed installation. Source CORS regex is intentionally exact, not wildcard.

## Verified local safety copy and recovery boundary

A private, root-owned backup was created **without stopping services**:

`/var/backups/montara-lab-fer-e2e-20261117`

Files:
- `owner-sqlite/{owners,pending,projects,sessions}.sqlite3`
- `broker-sqlite/jobs.sqlite3`
- `config/start.sh`, `config/montara-lab-fer-portal.service`
- `SHA256SUMS`

Copies of live SQLite databases were made using `sqlite3.Connection.backup()` and each returned `PRAGMA integrity_check = ok`. Every file passed `sha256sum -c` in an independent check. Keep owner data and especially sessions restricted to root; never attach them to an issue or archive them into a public repo.

**Limits:** this is **not** a full disk image, not a Windows Companion backup, not a Cloudflare configuration export, not a recovery guarantee for in-progress Engine processes, and it deliberately excludes OAuth secrets and video originals. Before restoration, inspect active jobs, shut down only isolated FER services under an explicit recovery procedure, back up the current state separately, restore with appropriate ACLs, and revalidate OAuth and stage. **Never overwrite live SQLite or kill an Engine mid-job.**

Safe inspection via authorized remote device using `ssh montara '<command>'`, avoiding printing private files:
```bash
systemctl --user is-active montara-lab-fer-portal.service
systemctl is-active montara-h4-fertrial-broker.service
ss -ltn | grep ':8126 '
sudo sh -c 'cd / && sha256sum -c /var/backups/montara-lab-fer-e2e-20261117/SHA256SUMS'
```

The last ledger check returned one `running` and two `stopped` Engine records. The existence of a `running` record alone is **not** proof of an actively rendering video, but do not stop a job without verification.

On the Windows host, confirm service health and allowlisted origin without posting tokens or logins:
```powershell
Invoke-RestMethod http://127.0.0.1:47820/health | Select-Object version,ffmpeg,busy
$origin = 'https://montara-lab-fer.memoriainvalida001.workers.dev'
(Invoke-WebRequest 'http://127.0.0.1:47820/health' -Headers @{Origin=$origin} -UseBasicParsing).Headers['Access-Control-Allow-Origin']
```
Expected header equals `$origin`. Verify an unrelated Origin does **not** gain CORS access. Native tray closing is not equivalent to terminating its child service. Never restart during `busy=true`.

## Open acceptance gaps and ownership

1. **First-save thumbnails:** on a fresh test project, compare `/api/v1/wizard/review?render=1&shot={index}` response image URLs and thumbnail requests before/after first `PATCH /api/v1/edit/shot`; instrument browser without collecting cookies or project media. Characterize first-save-only cache invalidation; add failing regression then targeted fix. Do not merge PR #243 as a bug *fix*; it currently adds coverage, not a runtime correction.
2. **Companion allowlist PR #249:** Windows QA build completed successfully, human Windows CORS and E2E pass. Linux composite CI has a failing engine job; check whether pre-existing/parity-related before any merge. Do not claim a wholly green CI matrix. Merge only after reviewer confirms scope and failure disposition, then rerun affected checks.
3. **Native project output:** with user-chosen project folder, Companion should save output to a contained `Exports` directory and expose `Open output folder`, not assume arbitrary browser download paths. Require path validation, user consent, collision handling, atomic writes and fallback `Download`. Coordinate with Chema because browser-only JS cannot silently choose unrestricted local filesystem paths.
4. **Windows wording:** replace `Mac` wording in shared editor with platform-neutral text or OS detection; do not assume Windows paths are available to remote server.
5. **Quality/performance:** repeat with reference media and measure proxy generation time/size, timeline sync, first-save network requests, render elapsed time, CPU/RAM per service, local final size and perceptual quality. A VM CPU graph alone does not measure Companion utilization.
6. **Rollout:** preserve FER private environment; integrate reviewed code in main, verify LAB-JM with Chema **without touching his running session**, and only then consider refactoring/benchmarks.

## Communication and issue log

Human observations, reproducible steps and private baseline are logged under [issue #216](https://github.com/amehcgracia-byte/Montara/issues/216). CORS correction [PR #249](https://github.com/amehcgracia-byte/Montara/pull/249); gallery regression [PR #243](https://github.com/amehcgracia-byte/Montara/pull/243).

**Operator rule:** the working LAB-FER environment is a protected reference, not a throwaway experiment. All diagnostic work runs in an isolated checkout or test project; don't deploy to FER or JM during live work without deliberate validation.
