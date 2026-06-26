# Feature Inventory

Last updated: 2026-06-26

## Implemented (Production Studio RC2, 2026-06-26)

| Feature | Evidence | Status |
|---|---|---|
| Long story improve (chunked) | `StoryEngine.improve_narration_script()` + `split_text_into_chunks()` in `backend/app/story_engine/engine.py`, `LONG_STORY_CHUNK_CHARS` setting | Working — verified with real Ollama on short (1 chunk) and synthetic long (2+ chunks) stories |
| Distinct Ollama error messages | `backend/app/ai_providers/ollama.py` (`Timeout`/`ConnectionError`/`HTTPError` handled separately) | Working — verified via mocked exception injection |
| Lightweight job/progress system | `backend/app/jobs.py`, `GET /api/jobs/{id}`, `GET /api/projects/{id}/jobs` | Working — local JSON, no DB/Redis/Celery |
| Job-based story improve/images/video/audio | `POST .../story/improve/jobs`, `.../images/generate-all/jobs`, `.../video/render/jobs`, `.../tts/generate-all/jobs` | Working — original synchronous endpoints unchanged |
| Project Timeline View | `frontend/src/App.tsx` "الخط الزمني" step | Working — derived from existing project/audio/image/video data |
| Project Asset Library | `frontend/src/App.tsx` "مكتبة الأصول" step | Working — every project file grouped with available/missing state, backend-proxied downloads |
| Quality Review Board | `Scene.review_status/review_notes`, "مراجعة الجودة" step | Working — persists via existing `PUT /api/projects/{id}` |
| Ken Burns / fade video mode | `Project.video_mode/video_transition`, `_build_segment_video_filter()` in `backend/app/routers/videos.py` | Working — ffmpeg `zoompan` + per-segment fade; static mode still default; duration-sync re-verified |
| Image prompt preview | `GET .../images/scenes/{id}/prompt-preview` | Working — read-only, no job spent |
| Simple Image Studio | `POST /api/images/standalone/jobs`, "استوديو الصور المستقل" step | Working — verified with one real small ComfyUI job |
| Safety & rights checklist | `Project.safety_source_type/safety_consent_confirmed/safety_rights_notes/safety_applies_to` | Working — informational only, never blocks flow |
| Model/engine status dashboard | `GET /api/system/status` | Working — aggregates existing health checks, no URLs/secrets exposed |

## Implemented (Production MVP, through 2026-06-25)

| Feature | Evidence | Status |
|---|---|---|
| Ollama health/config | `/health`, `/api/config`, `/api/ai/ollama/health` | Working |
| Story improvement | `POST /api/story/improve` | Working |
| Scene splitting | `POST /api/story/split-scenes` | Working |
| Project create/list/load/update/delete | `backend/app/routers/projects.py` | Working |
| Editable scene cards | `frontend/src/App.tsx` scene editor | Working |
| `scenes.json` export | `GET /api/projects/{project_id}/scenes.json` and frontend download | Working |
| Project ZIP export | `GET /api/projects/{project_id}/export.zip` | Working |
| TTS health bridge | `GET /api/tts/health` | Working when configured |
| Single TTS job bridge | `POST /api/projects/{project_id}/tts/jobs` | Working for current first-scene flow |
| TTS job polling | `GET /api/tts/jobs/{job_id}` | Working |
| Backend proxy audio download | `GET /api/tts/jobs/{job_id}/download/{format}` | Working |
| Generate all project audio | `POST /api/projects/{project_id}/tts/generate-all` | Working |
| Audio included in ZIP | `data/projects/{id}/audio` files included in export | Working |
| ComfyUI benchmark | `deploy/ai-server/comfyui-lab` | Technical PASS |
| Voice/language catalog | `GET /api/tts/voices` (Phase 1.5) | Working — static honest catalog, no invented options |
| Per-scene saved audio metadata | `GET /api/projects/{project_id}/audio` (Phase 1.5) | Working — verified on a real 6-scene project |
| Per-scene saved audio playback | `GET /api/projects/{project_id}/audio/{scene_id}` (Phase 1.5) | Working — real `<audio>` + download, no ZIP needed |
| Full-story playback | `GET /api/projects/{project_id}/audio/final_story.wav` (Phase 1.5) | Working — computed on demand, verified valid WAV |
| Audio Studio UX | Voice/language selectors, status copy, per-scene + full-story players in `App.tsx` | Working |
| Image worker bridge | `GET /api/images/health`, `POST .../images/jobs`, `GET /api/images/jobs/{id}`, `.../download` (Phase 2.1) | Working — backend-proxied to ComfyUI, verified with real generated PNGs |
| Story scene images | `POST .../images/scenes/{id}/generate`, `.../generate-all`, `GET .../images`, `.../images/{id}` (Phase 2.2) | Working — persisted, included in export.zip |
| Continuity bibles + style presets | `Project.story_style_bible/character_bible/location_bible/object_bible/negative_prompt/style_preset`, `GET /api/images/style-presets` (Phase 2.3) | Working — verified fix for a real style-drift bug |
| Video assembly | `POST .../video/render`, `GET .../video`, `.../video/download` (Phase 3.0) | Working — ffmpeg MP4, verified frame-by-frame |
| Subtitle export | `GET .../subtitles.srt`, `.../subtitles.vtt` (Phase 3.0/3.1) | Working — timing matches the rendered video exactly |
| Studio Workflow step navigation | `frontend/src/App.tsx` (`StudioStep`, `studio-stepper`) | Working — six steps (القصة، المشاهد، الصوت، الصور، الفيديو والترجمة، التصدير) instead of one long scroll; each step shows only its own panel |
| Per-step completion indicator | `studioSteps[].done` in `App.tsx` | Working — each step shows ✓ once it has data (story text, scenes, audio, images, video) |
| Unsaved-changes indicator | `isDirty` state in `App.tsx` | Working — project title shows "محفوظ" / "تغييرات غير محفوظة"; resets on load/save/delete |
| Busy-action spinner | `BusyNotice` component in `App.tsx` | Working — audio/image/video generation banners show a spinner instead of static text while running |
| Disabled-button explanations | `audioActionDisabledReason()`, `imageActionDisabledReason()` in `App.tsx` | Working — every disabled generate/export button explains why (no project saved, no scenes, service not configured) |
| Export step asset checklist | Export step `export-grid` in `App.tsx` | Working — lists ZIP, scenes.json, per-scene audio count, final story audio, image count, video, subtitles, each shown as available or explicitly missing |

## Implemented But Needs UX Polish

| Feature | Current Gap | Recommended Phase |
|---|---|---|
| Job progress (RC2) | `current_step`/`total_steps`/`message_ar` exist and are polled live; still no percentage/ETA by design (deliberately not faked) and no cancel/retry endpoint yet | Later hardening if needed |
| Image/video/audio synchronous endpoints | Original `.../images/scenes/{id}/generate`, `.../images/generate-all`, `.../video/render`, `.../tts/generate-all` still block the HTTP request until done -- kept for callers that don't need polling. The frontend itself now uses the `/jobs` variants for the long-running ones. | Stable as-is; both paths intentionally coexist |

## Benchmark-Only

| Area | Status | Notes |
|---|---|---|
| SILMA | PASS as isolated lab; blocked in worker by network during later attempt | Keep isolated, do not force into product |
| Piper | PASS in TTS worker | Current default practical engine |
| AllTalk/XTTS | Candidate | Needs real benchmark before product use |
| ComfyUI + SDXL | PASS, product-integrated | Quality `CANDIDATE`, not final product sign-off |
| Image continuity workflows | Tier 1 (prompt-only) implemented and verified | Pixel-level/face-locked continuity is a later tier |
| WanGP / image-to-video | Planned only | Not started, stays an isolated lab benchmark (Phase 3.2) |

## Planned / Not Started

| Feature | Planned Phase |
|---|---|
| Long-story image batching (3-6 scenes per batch for 10+ scene stories) | Phase 2.6 |
| Version History / Snapshots | Later product safety feature |
| Burned-in subtitles in MP4 / styling presets | Phase 3.1 |
| Subtitle Editor / word-level alignment | Phase 3.0 / 3.1 |
| Export presets | Phase 3.3 |
| Job system crash recovery / cancel endpoint | Later hardening, if multi-user/longer sessions need it |
| Split `App.tsx` step panels into components (StoryStep/ScenesStep/AudioStep/ImagesStep/VideoStep/TimelineStep/AssetsStep/ReviewStep/ImageStudioStep/ExportStep) | Deferred — each shares 15-30+ state/handlers; needs a live browser to verify safely, see `docs/DECISION_LOG.md` 2026-06-25 entry. App.tsx is now larger after RC2 (10 steps), making this more valuable but still deferred for the same reason. |
| Advanced Image Continuity (reference/seed/IPAdapter/ControlNet) | Mid-future, after benchmark |
| Local AI Assistant Lab | Phase 4.0 |
| Chat model benchmark | Phase 4.1 |
| Project Knowledge/RAG setup | Phase 4.2 |
| Web search benchmark | Phase 4.3 |
| Vision chat benchmark | Phase 4.4 |
| Story Studio assistant tools | Phase 4.5 |

## Current Recommendation

The Studio MVP pipeline (story → scenes → audio → scene images → continuity → video → subtitles → export) is implemented and verified end-to-end on a real fresh project. Next: Hamza's own manual QA pass (`docs/MANUAL_QA_CHECKLIST.md`). After sign-off, the recommended future track is documented in `docs/REMAINING_FEATURES_BACKLOG.md`: job queue/progress, timeline view, asset library, quality review board, then better ffmpeg video assembly.
