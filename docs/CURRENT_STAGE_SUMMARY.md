# Current Stage Summary

## Current Stage

**Stage:** Studio MVP — Final QA Pass (Milestone G)

**Status:** ✅ Studio MVP pipeline (story → scenes → audio → images → continuity → video → subtitles → export) is implemented, verified end-to-end with real data, and has passed the engineer-side QA/cleanup pass (stale `/health`/export `phase` metadata fixed, docs synced). Hamza's manual hands-on QA pass (`docs/MANUAL_QA_CHECKLIST.md`) is the only remaining step before picking the next roadmap track.

**Recommendation:** No new engineering for Studio MVP scope. Next: Hamza's manual QA pass, then a product decision on the next track (Phase 2.7 Production Studio Foundations, Phase 3.1 video polish, or Phase 4.x assistant lab).

## What Changed in This Phase

- `storage.py` gained `_build_srt()`/`_build_vtt()` (pure functions, no I/O) plus `build_srt()`/`build_vtt()` storage methods. One cue per scene, cumulative timing from `duration_seconds` — the exact same timeline Phase 3.0's video assembly already uses, so subtitles and video stay in sync by construction.
- New `GET /api/projects/{id}/subtitles.srt` and `.../subtitles.vtt` in `projects.py` — both generate on demand (no job, no persistence needed; regenerating from current `narration_ar` is essentially free, unlike audio/image/video which call external engines or ffmpeg).
- `build_export_zip()` now always includes `subtitles/story.srt` and `subtitles/story.vtt` (not conditional on anything, since generation has no prerequisites beyond having scenes).
- Frontend: two plain download links ("تحميل الترجمة (.srt)" / "(.vtt)") next to the existing scenes.json/ZIP downloads — no job UI needed since generation is synchronous and instant.

## Verified End-to-End (real, not simulated)

- Real 6-scene project → both `.srt` and `.vtt` generated with correct Arabic RTL text (no mojibake), correctly formatted timestamps (`00:00:00,000` for SRT, `00:00:00.000` for VTT), and cumulative timing that sums to exactly 52 seconds — matching Phase 3.0's rendered video duration precisely.
- Zero-scene project → `200` with an effectively empty file, not an error.
- Nonexistent project → `404`.
- `export.zip` → now 20 files (audio + images + video + both subtitle files), no corruption.
- Security grep on both subtitle responses → clean (no AI Server address/path leakage, though this endpoint never touches the AI Server anyway).
- Full regression: `check_utf8`, `compileall`, `docker compose config`, frontend build, smoke test — all pass.

## Do Not Do Yet

- لا محاذاة على مستوى الكلمة (word-level alignment) — كل مشهد سطر ترجمة واحد بمدته الكاملة، هذا Phase 3.1+ المتقدم.
- لا حرق الترجمة داخل الفيديو (burn-in) ولا أنماط ترجمة بصرية (lower-third سينمائي، إلخ) — تلك خارج هذا الـMVP.
- لا ترجمة إنجليزية تلقائية بعد — فقط العربية من narration_ar الموجود.
