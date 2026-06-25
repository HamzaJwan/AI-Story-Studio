# Audio UX Plan — Phase 1.5

Last updated: 2026-06-25

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

## Acceptance Criteria

- User can check TTS health.
- User can generate first-scene audio and play it in the browser.
- User can generate all project audio and see which scenes have audio.
- User can play/download each saved scene audio without opening ZIP manually.
- User can play/download full project audio if generated.
- Voice/language controls work with one available voice and do not break if only Arabic Piper is available.
- `export.zip` still includes scene audio and `final_story.wav`.
- Browser never calls AI Server directly.
- `python scripts/check_utf8.py`, `python -m compileall backend/app`, `docker compose config`, and frontend build pass.

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

