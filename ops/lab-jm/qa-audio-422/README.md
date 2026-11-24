# LAB-JM Companion QA: HTTP 422 classification + per-track retry candidate

**Scope:** Issue #278, only the isolated QA Companion transport on port 47830. Does not modify the habitual Companion at 47820, shared F1 proxy interfaces, Windows/FER, MAIN, or the multi-track pipeline.

## Why
The installed QA `beta_audio` handler maps `ValueError`, `OSError`, `RuntimeError`, `KeyError` and `URLError` indiscriminately to HTTP 422. A generic 422 says nothing about whether a retry is safe. No observed real failing 422 was traced to one specific exception; this patch is a classification contract, **not** a claim that the previous five 422s were transient.

## Classification contract

- `AUDIO_TEMPORARY_IO` / `AUDIO_TEMPORARY_TIMEOUT`: HTTP 503 + `retryable:true`. A timeout must be explicitly raised as `TimeoutError`; unknown RuntimeErrors remain permanent.
- Invalid payload/collision, disallowed authorization, missing original/job, unsupported encoder/format, unknown runtime error: no automatic retries. 403/404/422 with safe non-retryable codes. Disk-full: 507 + `retryable:false`.
- Error bodies contain constant text and enumerated safe codes only. No names, paths, IDs, hashes, tokens or stderr.
- `retry_audio_track.js` is a **client integration helper**, not a new endpoint or a standalone active browser feature. It retries only explicitly whitelisted codes with `retryable:true`, using same `jobId`/`payloadJson`, a *fresh grant* each time, 400/800-ms backoff, maximum 3 attempts. Cancellation stops it. Do not rerun a batch or upload original WAVs.
- Existing `BetaAudioJobs.authorize()` keeps binding each retry to the same job, payload hash, workspace, original and cached conversion. Leave `BoundedSemaphore(2)` unchanged.

## Reproducible safe application (after review)

`python3 ops/lab-jm/qa-audio-422/patch_qa.py "/Applications/Montara Beta Main Companion QA.app/Contents/Resources/companion/companion.py" /tmp/qa-audio-review-output`

The command only creates review files under the explicitly supplied output directory. It refuses any changed QA source hash, uses a unique handler anchor, compiles the result, and **never installs, restarts, signs, or modifies the app**. To deploy later, a separately authorized installation procedure must back up QA, install the classifier+patched handler, connect the actual QA caller to the retry helper and validate authorized 47830 calls; revert both files if any regression occurs. This is deliberately not deployed under the current task.

## Tests

`python3 -m unittest discover -s ops/lab-jm/qa-audio-422 -p 'test_qa_audio_failures.py' -v`

`node --test ops/lab-jm/qa-audio-422/test_retry_audio_track.cjs`

Acceptance still needed: real authenticated 47830 transient/permanent QA responses; no repeated completed proxies; cancellation and cache reuse; 16 independent input tracks; full Mixer export. No claim of user E2E before these gates.
