# #386 / #115 — 360 export baseline and cache-volume fix

Read-only inspection of two completed Companion macOS jobs, 23 Nov 2026. User media and production processes were not modified.

| Metric | Insel.Gig.mp4 | Half the Funk dos.mp4 |
|---|---:|---:|
| Source 360 original | 3840×1920, 436.64s | 3840×1920, 728.88s |
| Final | 1920×1080 H.264/AAC, 403.567s | 1920×1080 H.264/AAC, 727.133s |
| Video bitrate | ~18.31 Mb/s | ~18.54 Mb/s |
| Byte size | 934,175,129 | 1,703,722,769 |
| Full render wall | 1265.2s | 2125.43s |
| 360 source preparation | 732.281s | 1164.854s |
| Segment count | 75 | 205 |
| 360 export intermediate segments | 24 | 59 |
| Segments rendered from source | 51 | 146 |
| Segment cache hits | 0 | 0 |

**Observed root cause:** Companion `video_jobs.py` used `~/.montara-companion/video/spherical-cache/<engine>`, whereas the projects and `.montara-renders` workspaces are on the external `/Volumes/AMEHC` filesystem. Runtime `st_dev` differs. `retain_spherical_cache` in `local_video.py` uses `os.link()`; cross-device links fail with `EXDEV` and are silently skipped. Cache directory had no `equirect-*.mp4` entries. Mac internal storage had ~16.45 GiB free while the external drive had ~1219.45 GiB free, so copying multi-GB spherical intermediate files into internal storage is unsafe and unnecessary.

**Change (draft only):** Companion now uses `<selected project>/.montara-renders/.spherical-cache/<engine>` for the spherical intermediate cache. This is on the same volume as the render `work`, and it tries hard-link retention first; on **ExFAT**, which does not support links (errno 45), it falls back to an fsynced sibling temporary copy and atomic replace, with an 8 GiB free-space reserve enforced **after** accounting for the duplicate bytes. It retains the 16 GiB cache cap, source signature, resolution/version key, and symlink restrictions. Scoped **per project**, not globally across projects; a given project's next export can reuse high-quality 360 intermediate when its original and cache key remain the same. No alteration to source paths, codecs, frames, or final export quality. No migration of old cache, user files, or uploads.

**Synthetic QA:** path contract, APFS hard-link retain→restore byte-exact and inode-equivalent, forced ExFAT `ENOTSUP` atomic-copy restore byte-exact, rejection of symlinks and empty intermediates. 4 tests PASS. No real second export benchmark or user-visible deployment has occurred; true speedup remains to be measured with a cold/warm replay of the same source, quality profile and Engine version.

**Quality follow-up #115:** local export uses fingerprint-verified full originals; 360 non-moving source can be transcoded to a 3840×1920 H.264 CRF18 export intermediate, and final output is 1080p at ~18Mb/s. This does not prove preservation of visual detail in 360 crops; a controlled matched-frame comparison of original 360 / intermediate / final (with equivalent projection, FOV, timestamp) is needed before changing encoder bitrate, resolution, projection or sharpening. There is no 2GB quality improvement claim until such comparison is done.


### Follow-up: ExFAT discovery and real-source microbenchmark (23 Nov)

Actual mounted `/Volumes/AMEHC` is **ExFAT** (not APFS). Both the original cross-volume hard-link approach and the first draft same-volume hard-link-only implementation failed; direct probe of `os.link()` on this ExFAT volume returns errno **45** (`Operation not supported`). PR now has safe atomic-copy fallback for `ENOTSUP` / `EXDEV`. One 2-second actual source-360 sample (3840×1920, x264 `ultrafast` CRF18) encoded in **2.345s**; persisted the 8,334,115-byte intermediate via atomic cache copy **0.1677s** and restored the warm cache **0.0615s**. This is a microbenchmark, NOT evidence of a 12–19-minute saving on a full concert. ExFAT copies do not share inode, unlike hard links, and hence consume extra external disk space, within the 16 GiB per-project cache cap. No user files were changed; the temporary sample was cleaned.

### Quality matched-frame spot-check

For `Insel.Gig`, first saved shot is a static equirectangular 360 view (`yaw=-179`, `pitch=-24`, v360 rectilinear, h_fov=110, v_fov≈77.552). Projected a frame from the **real 3840×1920 original at 31.272s**, compared it to a **fresh 0.8s *synthetic* CRF18 intermediate** and the **existing final output near 1.0s**. FFmpeg SSIM versus the original-projected reference: **0.978099** for the synthetic intermediate projection and **0.913909** for the final MP4 frame. SSIM of final includes approximate temporal alignment, color, scale and subsequent encoding; it **cannot** uniquely measure the compression loss from the intermediate. The actual intermediate for these historical renders was not preserved, so no claim of an exact archived-intermediate comparison or full visual acceptance. An explicit matched 360 still comparison can be rerun on a new project once cache persistence is installed.
