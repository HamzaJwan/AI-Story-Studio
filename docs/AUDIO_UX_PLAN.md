# Audio UX Plan — Phase 1.5

Last updated: 2026-06-25

**Status: ✅ Implemented and manually verified end-to-end (real audio, real playback, real persistence).**

## Why Phase 1.5

Audio generation already works, but the current product experience is incomplete. Users can generate audio and find it in ZIP output, yet they need clear browser playback, per-scene controls, a full-story player, and graceful voice/language controls.

## Current Audio State

- `GET /api/tts/health` checks backend-to-worker connectivity.
- `POST /api/projects/{project_id}/tts/jobs` creates a single scene/project job.
- `GET /api/tts/jobs/{job_id}` polls job status.
- `GET /api/tts/jobs/{job_id}/download/{format}` proxies generated audio through the backend.
- `POST /api/projects/{project_id}/tts/generate-all` generates and saves per-scene WAV files.
- `export.zip` includes scene WAV files and `audio/final_story.wav`.

## UX Gaps

- The user cannot easily play saved scene audio after `generate-all`.
- The user cannot play/download `final_story.wav` directly in the app.
- Voice and language are not selectable in the UI.
- If only one voice exists, the UI should show it as selected/disabled rather than fail.
- Job progress is coarse and not scene-aware for `generate-all`.
- The hero phase label/status is stale.

## Phase 1.5 Scope

### Backend

Allowed lightweight additions:

- `GET /api/tts/voices`
- `GET /api/projects/{project_id}/audio`
- `GET /api/projects/{project_id}/audio/{scene_id}`
- `GET /api/projects/{project_id}/audio/final_story.wav`

Rules:

- All audio must stream through the backend.
- Do not expose `TTS_SERVICE_URL`.
- Do not add a new TTS engine.
- Do not touch image/video/deploy pipelines.
- Do not break `export.zip`.

### Frontend

Add:

- Voice selector.
- Language selector.
- Single-scene audio player after generation.
- Per-scene play/download controls when saved audio exists.
- Full-story player/download when `final_story.wav` exists.
- Better status copy for queued/running/done/failed.
- Graceful empty states.

Keep:

- RTL Arabic UX.
- Current project workspace flow.
- Existing project save/load/edit/export behavior.

## Acceptance Criteria — all verified with real requests, not assumed

- ✅ User can check TTS health (`remote_ok: true`, real LAN latency to the AI Server worker).
- ✅ User can generate first-scene audio and play it in the browser (`<audio>` + download appear only after `status: "done"`).
- ✅ User can generate all project audio (`generate-all` on a real 6-scene project: `6/6` generated, `0` failed) and see which scenes have audio.
- ✅ User can play/download each saved scene audio without opening the ZIP manually — `GET /api/projects/{id}/audio/{scene_id}` streams real WAV through the backend.
- ✅ User can play/download full project audio if generated — `GET /api/projects/{id}/audio/final_story.wav`, verified as a valid concatenated WAV (53.63s for 6 real scenes).
- ✅ Voice/language controls work with one available voice (`ar_JO-kareem-medium`) and do not break — `GET /api/tts/voices` always returns this catalog, with a frontend hardcoded fallback if the call ever fails.
- ✅ `export.zip` still includes scene audio and `final_story.wav` (verified: 11 files including 6 scene WAVs + `final_story.wav`), and still returns `200` for a zero-scene project (no regression).
- ✅ Browser never calls AI Server directly — confirmed by grepping every Phase 1.5 response for the AI Server's LAN address/port and for `/workspace` filesystem paths. Found and fixed one real gap: `GET /api/tts/jobs/{job_id}` was leaking `files[].path` (an internal container path) — stripped before this phase shipped.
- ✅ `python scripts/check_utf8.py`, `python -m compileall backend/app`, `docker compose config`, and `docker compose exec frontend npm run build` all pass.

## Implementation Notes

- `final_story.wav` is computed on demand from current scene audio (not cached as a separate file), so it can never go stale relative to `export.zip`'s own concatenation.
- `GET /api/projects/{project_id}/audio/{scene_id}` resolves the scene by ID against the project's actual scene list, then verifies the resulting path stays inside that project's audio directory before reading — defends against path traversal even if a `scene_id` were ever attacker-influenced via a project update.
- The "generate first-scene audio" button intentionally stays ephemeral (job-based, not persisted) — only `generate-all` persists per-scene audio to disk/metadata, matching the existing Phase 1.3/1.4 design split.

## Practical Patterns

- Long-running media operations should return a job/status resource and be polled instead of blocking the UI.
- Browser playback can use normal `<audio controls>` elements with backend-proxied WAV/MP3 URLs.
- Piper voice selection is model-based; each language/voice usually maps to a specific voice model/config, so the UI should treat voice and language as worker capabilities, not arbitrary free text.

## Sources

- FastAPI custom responses and response models: https://fastapi.tiangolo.com/advanced/custom-response/
- Long-running REST job pattern: https://restfulapi.net/rest-api-design-for-long-running-tasks/
- Piper repository: https://github.com/rhasspy/piper
- Piper voice samples: https://rhasspy.github.io/piper-samples/
- Piper training/voice model structure: https://github.com/rhasspy/piper/blob/master/TRAINING.md

