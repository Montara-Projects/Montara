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

**Change (draft only):** Companion now uses `<selected project>/.montara-renders/.spherical-cache/<engine>` for the spherical intermediate cache. This is on the same volume as the render `work` and uses existing hard-link, 16 GiB cache cap, 8 GiB free reserve, source signature, resolution/version key, and symlink restrictions. Scoped **per project**, not globally across projects; a given project's next export can reuse high-quality 360 intermediate when its original and cache key remain the same. No alteration to source paths, codecs, frames, or final export quality. No migration of old cache, user files, or uploads.

**Synthetic QA:** path contract, hard-link retain→restore byte-exact and inode-equivalent, rejection of symlinks and empty intermediates. No real second export benchmark or user-visible deployment has occurred; true speedup remains to be measured with a cold/warm replay of the same source, quality profile and Engine version.

**Quality follow-up #115:** local export uses fingerprint-verified full originals; 360 non-moving source can be transcoded to a 3840×1920 H.264 CRF18 export intermediate, and final output is 1080p at ~18Mb/s. This does not prove preservation of visual detail in 360 crops; a controlled matched-frame comparison of original 360 / intermediate / final (with equivalent projection, FOV, timestamp) is needed before changing encoder bitrate, resolution, projection or sharpening. There is no 2GB quality improvement claim until such comparison is done.
