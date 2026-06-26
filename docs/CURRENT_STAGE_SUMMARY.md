# Current Stage Summary

## Current Stage

**Stage:** AI Story Studio — Production Studio RC2

**Status:** ✅ Studio MVP pipeline (story → scenes → audio → images → continuity → video → subtitles → export) is implemented and verified end-to-end with real data, and the Production Studio Foundations track (Phase 2.7) is now also complete: long stories improve in chunks instead of failing, a lightweight local job/progress system replaces blind "جاري..." waits for story-improve/audio/image/video, and four new workflow steps were added -- Timeline View, Asset Library, Quality Review Board, and a standalone Simple Image Studio -- plus an optional Ken Burns/fade video mode, a story-bible prompt preview, a lightweight safety/rights checklist, and a model/engine status dashboard. Hamza's manual hands-on QA pass over these RC2 additions (`docs/MANUAL_QA_CHECKLIST.md`) is the only remaining step.

**Recommendation:** No new engineering beyond RC2 for the current scope. Next: Hamza's manual QA pass over the new Timeline/Asset Library/Review Board/Ken Burns/Image Studio surfaces, then a product decision on the next track (advanced image continuity, export presets, or Phase 4.x assistant lab -- see `docs/REMAINING_FEATURES_BACKLOG.md`).

**Expected output, set expectations correctly:** a video composited from scene images (static, or a light ffmpeg-only Ken Burns zoom) + generated narration audio + subtitle timing — no AI-driven motion (no Veo/Runway/WanGP-style video). Image quality is `CANDIDATE`, not final production quality. The job/progress system is local-only (no Redis/Celery/DB) and has no crash recovery. See "Known Limitations" below.

## What Changed in This Phase (Production Studio RC2, 2026-06-26)

- **Long story improve fix:** `OllamaProvider` now distinguishes timeout/connection/HTTP errors instead of one misleading "service unreachable" message; stories over `LONG_STORY_CHUNK_CHARS` (default 6000) are split into ordered chunks and improved sequentially.
- **Job/progress foundation:** local JSON job records (`data/jobs/`, gitignored) with `queued/running/done/failed/cancelled` status; `/jobs` variants for story-improve, images generate-all, video render, and audio generate-all, polled by the frontend with live per-step Arabic messages. Original synchronous endpoints unchanged.
- **Project Timeline View, Asset Library, Quality Review Board:** three new workflow steps surfacing per-scene production state, every downloadable file, and approve/needs_retry/reject review state -- all derived from existing data, no new heavy backend logic.
- **Ken Burns video mode:** optional ffmpeg-only `zoompan` zoom-in and per-segment fade, selectable per project; static mode remains default; the existing audio-duration-sync guarantee re-verified for this mode.
- **Prompt preview + Simple Image Studio:** a read-only endpoint shows the exact assembled image prompt before spending a job; a new standalone "one prompt, one image" studio is fully separate from scene images.
- **Safety checklist + engine dashboard:** lightweight informational project metadata (source/consent/rights notes) and one aggregated Ollama/TTS/image/ffmpeg status view, with no URLs or secrets exposed.

Full detail and verification evidence: `docs/PRODUCTION_STUDIO_RC2_REPORT.md` and `docs/DECISION_LOG.md`.

## What Changed in the Prior Phase (Subtitle Export MVP)

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

## Known Limitations (RC1, documented not hidden)

- **جودة الصور `CANDIDATE`** — ComfyUI/SDXL تقني PASS، لكن لم تُعتمد كجودة نهائية للمنتج. الاستمرارية prompt-only (Tier 1)، ليست pixel-level/face-locked.
- **الفيديو تجميع ffmpeg، ليس AI video** — صور ثابتة + صوت + قطع حاد بدون حركة، ليس Veo/Runway/WanGP. حركة AI حقيقية مخططة لاحقاً (Phase 3.2، lab منفصل).
- **Endpoints الصور/الفيديو/الصوت لها الآن نسخة job-based اختيارية** (`.../jobs`) لا تحجب الطلب، لكن نظام الـjobs محلي فقط (ملفات JSON تحت `data/jobs/`) بدون Redis/Celery/قاعدة بيانات، وبدون استرجاع تلقائي إذا تعطّل الـbackend وسط عملية — مقبول لمستخدم واحد محلي، ليس جاهزاً لمستخدمين متزامنين.
- **Ken Burns ليس حركة AI حقيقية** — تقريب/تلاشي بسيط عبر ffmpeg فقط (zoompan + fade)، والتلاشي داخل كل مشهد لا بين مشهدين (ليس crossfade حقيقي)، توضيح متاح في الواجهة.
- **استمرارية الصور تبقى Tier 1 (prompt-only)** — معاينة الـprompt الجديدة توضّح ما يُرسل لكنها لا تضيف ثباتاً فعلياً بدون reference workflow (IPAdapter/ControlNet) لاحقاً.
- **لا مساعد AI محلي بعد** — Phase 4.x، لاحقاً، يبقى docs-only.
- **generated media لا يدخل Git أبداً** — كل شيء تحت `data/projects/{id}/` مستثنى بـ `.gitignore`.
