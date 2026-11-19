# Engine single-shot parity — issue #254 (2026-11-19)

## Contract and observed regression

The six red cases in Montara's `e2e(engine) → Engine lighting, framing and preview parity` were reproduced on the exact JM/Main Engine pin `92c7bc33f59baae92a8d61e5dd4bf0ce9685d79e` (6 failed). These are distinct from unrelated Session, OAuth, UI and Companion failures.

| Cases | Baseline failure | Resolution / non-regression check |
| --- | --- | --- |
| 3 × `test_video_light.py` | Camera-wide edits previously expected HTTP 200 but strict single-shot now correctly returns HTTP 400 | Explicitly test rejection and unchanged plan bytes; then accept a legitimate one-shot edit and prove the other shots are untouched, including same source and camera ID |
| 2 × `test_flat_framing.py` | Tests expected the previous 6% crop motion, while the actual authored motion is 14% | Preserve the 14% movement/direction contract and compare decoded preview/export pixels, not only filter strings |
| 1 × `test_stage_performers.py` | Actual FFmpeg closeup rendered a white head within one pixel of the top edge | Protect against the full 14% opening zoom, increase vertical headroom, retain rendered head and no-neighbor assertions for every frame |

Engine PR: https://github.com/amehcgracia-byte/zucker_videos/pull/76
Candidate Engine commit: `9af275b18535005e36bd289a68ceb4a1d2f6c506`, direct descendant of `92c7bc3`.
The renderer and performer crop now share `FIXED_CROP_MOTION_ZOOM`; performer analysis cache version increases from 8 to 9 to invalidate obsolete crops.

## Pin comparison — do not silently promote/downgrade a lab

- Montara Git main before this change: `051c58130ad512aa05e841effc4f5651ca04a188`; Engine gitlink `92c7bc3`.
- LAB-FER Windows Companion (reported): Engine `b867b3c72af8fe4685b487bcf1e09ffcc2a7c82b`.
- Verified Engine Git ancestry: `b867b3c` **is an ancestor** of `92c7bc3`, with 39 commits on the JM side. The candidate `9af275b` adds one more commit. The ancestry relation is a Git fact, **not** proof of API or rendering compatibility for LAB-FER.
- Comparing the pins changes `core/fixed_camera_moves.py`, `core/shot_review.py`, `core/stages/{edit,export}.py`, `core/video_light.py`, `server/{api,edit_timeline}.py` and several isolation/quality tests. A direct LAB-FER pin replacement is not part of issue #254.
- No deploy to LAB-FER, LAB-JM, MAIN, Work or any live Companion. No runtime services, user media, stored projects or credentials touched.

## Tests and merge gates

Baseline reproduction: exactly six named failed tests (Mac local checkout at `92c7bc3`).
The 17-file Engine test selection from `.github/workflows/e2e.yml` passed **226 tests on macOS / Python 3.11** before the final shared-constant/cache-invalidation refinement; after that, the three affected modules passed **45 tests**, and decoded preview/export pixel parity passed separately. The final complete re-run and GitHub Linux CI must be reported in the PR before merging.

The Engine CI command is the unchanged `Engine lighting, framing and preview parity` command in `.github/workflows/e2e.yml`. There are **no new skips or xfails**. A green Mac run is not a Linux CI run, and targeted tests are not an E2E browser/MP4 acceptance.

Integration gates: (1) true green Linux `e2e(engine)`; (2) cross-lab review in #216 before changing the Engine pin; (3) explicit human approval for service deployments. Root PR remains draft until gates are met. Rollback is to reset the Engine gitlink from `9af275b` to `92c7bc3` by a new commit (never force-push), without modifying either live environment.
