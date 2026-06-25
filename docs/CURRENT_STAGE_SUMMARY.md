# Current Stage Summary

## Current Stage

**Stage:** Phase 1.5 — Audio UX Polish

**Status:** ✅ Implemented and manually verified end-to-end with real audio, real playback, real persistence.

**Recommendation:** Hamza's image quality sign-off (unblocks Phase 2.1), or a Manual QA Pack / `App.tsx` cleanup pass — see "Next Action" below. Do not start Phase 2.1 automatically.

## Verified Product State

- Phase 0.1 is stable: Ollama connection, story improvement, scene splitting, and `scenes.json` generation work.
- Phase 0.2 is stable: local project creation, saving, loading, scene editing, and edited `scenes.json` export work.
- Phase 0.3 and 0.4 are completed: scene editing UX polish and project ZIP export are available.
- Phase 1.x audio path is functionally proven with an external AI Server worker and project audio export.
- **Phase 1.5 is implemented:** voice/language catalog, per-scene saved audio playback, full-story playback, and clearer job status are all real and backend-proxied — no more forcing users to open the ZIP to hear anything.
- Phase 2.0 image benchmark is technically proven: ComfyUI + SDXL generated a real PNG on the AI Server. Still pending Hamza's quality approval.

## What Changed in Phase 1.5

**Backend** (`backend/app/routers/tts.py`, `backend/app/storage.py`):
- `GET /api/tts/voices` — static, honest voice/language catalog (the deployed worker has no list-voices capability; this reflects what's actually configured, `ar_JO-kareem-medium` via Piper, instead of inventing options).
- `GET /api/projects/{project_id}/audio` — per-scene + full-story saved-audio metadata, with backend-relative URLs only.
- `GET /api/projects/{project_id}/audio/{scene_id}` — streams saved scene audio, path-traversal safe (resolved against the project's real scene list and audio directory).
- `GET /api/projects/{project_id}/audio/final_story.wav` — streams the same raw-WAV concatenation `export.zip` uses, computed on demand (always in sync, never stale).
- `storage.py` gained `get_scenes_with_audio()`, `get_scene_audio_path()`, `build_final_story_wav()` — `build_export_zip()` now reuses the first instead of duplicating the scan logic.
- **Fixed a real gap found while testing:** `GET /api/tts/jobs/{job_id}` (and the job object returned by `POST .../tts/jobs`) was leaking the worker's internal container path (`files[].path`, e.g. `/workspace/data/jobs/...`). Stripped before this phase shipped — the frontend never read that field, so this is a safe, backward-compatible fix, not a breaking change.

**Frontend** (`frontend/src/App.tsx`, `frontend/src/styles.css`):
- Hero phase label fixed (was stale "Phase 0.4", now "Phase 1.5 — استوديو الصوت").
- Voice selector (single real option, shown selected; gracefully falls back to a hardcoded default if the endpoint ever fails) and a disabled-Arabic-only language selector.
- Clearer Arabic status copy: "خدمة الصوت متصلة" / "غير مفعّلة" / "غير متصلة" / "جاري الفحص...".
- Per-scene saved-audio list (play + download + size) populated from `GET /api/projects/{id}/audio`, refreshed automatically on project load and after `generate-all`.
- Full-story player + download when `final_story.wav` exists.
- "توليد صوت المشروع" no longer just says "download the ZIP" — it reports a real generated/failed count and immediately shows the per-scene players.

## Verified End-to-End (real, not simulated)

- `POST .../tts/jobs` with a real saved scene + `voice_id` → real Piper WAV, downloaded through the backend proxy.
- `POST .../tts/generate-all` on a real 6-scene project → `6/6` generated, `0` failed, all persisted with metadata.
- `GET .../audio` reflects the real persisted state correctly, including after a backend container restart (disk-persisted, not in-memory).
- `GET .../audio/{scene_id}` and `GET .../audio/final_story.wav` both stream real, valid WAV (verified with Python's `wave` module — correct sample rate and duration, not silence/corruption).
- Path traversal attempts (`../../etc/passwd`-style `scene_id` values) return `404`, not a file.
- `export.zip` still includes all scene audio + `final_story.wav` (11 files for a 6-scene project) and still returns `200` for a zero-scene project.
- Grepped every Phase 1.5 response for the AI Server's LAN address/port and for `/workspace` — clean after the job-endpoint fix above.
- Full regression: `check_utf8`, backend `compileall`, `docker compose config`, frontend `npm run build`, `smoke_phase0_workspace.py` — all pass.

## Next Action

1. Commit and push Phase 1.5.
2. Wait for Hamza's decision on the next step (image quality sign-off, Manual QA Pack, or `App.tsx` cleanup) — do not start Phase 2.1 automatically.

## Do Not Do Yet

- لا Image Worker Bridge (Phase 2.1) ولا أي UI صور قبل موافقة حمزة الصريحة على الجودة.
- لا فيديو (Phase 3.0) قبل حسم الصور بالكامل.
- لا محرك TTS جديد ولا تشغيل SILMA/AllTalk benchmarks.
