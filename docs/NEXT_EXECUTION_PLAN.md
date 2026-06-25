# Next Execution Plan

Last updated: 2026-06-25

## Recommended Next Phase

**Phase 1.5 — Audio UX Polish**

## Why

- The audio path is already technically working.
- Hamza has manually confirmed generated WAV files exist and can be exported.
- The current UX still pushes users toward ZIP inspection instead of direct playback.
- Phase 2.1 image work still requires image quality approval and continuity planning.

## Do Not Do Next

- Do not start Phase 2.1 yet.
- Do not add image generation UI.
- Do not start video work.
- Do not add a new TTS engine.
- Do not run SILMA/AllTalk benchmarks.
- Do not expose AI Server URLs to the browser.
- Do not touch `.env` or commit generated media.

## SONNET_NEXT_EXECUTION_PROMPT

You are now Executor inside AI Story Studio.

Task: implement **Phase 1.5 — Audio UX Polish** only.

Current state:

- Phase 0.1–0.4 core story/project/export workflow works.
- Phase 1.1–1.4 audio backend path works with an external TTS worker.
- Project audio can be generated and included in `export.zip`.
- Current UI has a limited Audio Studio panel, a single-job player, and project audio generation, but users still need ZIP inspection to find saved audio.
- Phase 2.0 image benchmark is technical PASS, but image work is paused until Hamza approves quality.

Goal:

Improve the existing audio UX without adding new AI engines or touching image/video work.

Expected files to modify:

- `backend/app/routers/tts.py`
- `backend/app/storage.py`
- `backend/app/schemas.py` if needed
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `docs/API_CONTRACTS.md`
- `docs/CURRENT_STAGE_SUMMARY.md`
- `docs/DECISION_LOG.md`

Forbidden:

- Do not touch `.env`.
- Do not add a new TTS engine.
- Do not integrate SILMA/AllTalk.
- Do not run SILMA/AllTalk benchmarks.
- Do not add image/video features.
- Do not modify `deploy/ai-server` except docs if absolutely necessary.
- Do not expose `TTS_SERVICE_URL` or any AI Server URL to the browser.
- Do not add generated WAV/MP3/ZIP/data files to Git.
- Do not use direct browser-to-AI-Server calls.

Backend requirements:

1. Keep existing endpoints working:
   - `GET /api/tts/health`
   - `POST /api/projects/{project_id}/tts/jobs`
   - `GET /api/tts/jobs/{job_id}`
   - `GET /api/tts/jobs/{job_id}/download/{format}`
   - `POST /api/projects/{project_id}/tts/generate-all`
   - `GET /api/projects/{project_id}/export.zip`
2. Add lightweight proxy/storage endpoints only if needed:
   - `GET /api/tts/voices`
   - `GET /api/projects/{project_id}/audio`
   - `GET /api/projects/{project_id}/audio/{scene_id}`
   - `GET /api/projects/{project_id}/audio/final_story.wav`
3. Voice/language behavior:
   - If the worker supports only one voice, return one selected option.
   - Do not fail the UI because multiple voices are unavailable.
   - Do not invent unsupported voices.
4. Audio streaming:
   - Serve saved project audio through the backend.
   - Prevent path traversal.
   - Do not expose filesystem paths or AI Server URLs.

Frontend requirements:

1. Fix stale visible phase/status label.
2. Add voice selector and language selector in Audio Studio.
3. If only one voice/language is available, show it selected and disabled/graceful.
4. Keep current “Generate first scene audio” behavior, but show a player when done.
5. After “Generate project audio”, show saved per-scene audio state.
6. Add per-scene play/download controls for generated scene audio.
7. Add full project audio player/download if `final_story.wav` exists.
8. Show clear statuses:
   - not configured
   - checking
   - queued
   - running
   - done
   - failed
9. Keep RTL Arabic-friendly design.
10. Do not break project save/load/edit/export or `scenes.json`.

Acceptance criteria:

- TTS health check works.
- First scene audio can be generated and played in the browser.
- Project audio can be generated.
- Saved scene audio can be played/downloaded without opening ZIP manually.
- Full-story audio can be played/downloaded if available.
- `export.zip` still includes audio.
- Voice/language selector does not break with a single Piper Arabic voice.
- Browser never calls AI Server directly.
- No generated audio files are staged in Git.

Validation:

Run:

```powershell
python scripts/check_utf8.py
python -m compileall backend/app
docker compose config
docker compose exec -T frontend npm run build
```

Manual test:

1. Open `http://localhost:5173`.
2. Load or create a project with scenes.
3. Check TTS health.
4. Generate first scene audio.
5. Confirm player appears and audio plays.
6. Generate project audio.
7. Confirm per-scene audio controls appear.
8. Confirm full project audio appears if generated.
9. Download project ZIP and confirm audio still exists.

Commit message:

```text
feat: polish audio studio UX
```

Final report format:

1. Files changed.
2. Endpoints added/changed.
3. Audio UX behavior implemented.
4. Validation results.
5. Manual test result.
6. Git status.
7. Confirm no image/video work was started.

