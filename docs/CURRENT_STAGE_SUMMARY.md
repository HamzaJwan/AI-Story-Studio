# Current Stage Summary

## Current Stage

**Stage:** Phase 2.1 — Image Worker Bridge

**Status:** ✅ Implemented and verified with real generated images for real scenes.

**Recommendation:** Continuing the Studio MVP Autopilot round (Milestone C — Story Scene Images MVP next). Image quality remains `CANDIDATE`, not final-approved — see `docs/IMAGE_QUALITY_APPROVAL_CHECKLIST.md`.

## What Changed in Phase 2.1

- `deploy/ai-server/comfyui-lab/`: now a **persistent** service (`restart: unless-stopped`), not a one-off benchmark container.
- `backend/app/ai_providers/image_worker.py`: talks directly to ComfyUI's native API (`/prompt`, `/history`, `/view`) — no custom FastAPI wrapper needed, unlike SILMA/Piper.
- New endpoints: `GET /api/images/health`, `POST /api/projects/{id}/images/jobs` (derives prompt from `scene.image_prompt_en`), `GET /api/images/jobs/{job_id}`, `GET /api/images/jobs/{job_id}/download` — all backend-proxied, same security boundary as the TTS bridge.
- Frontend: minimal "استوديو الصور" panel — health check, generate first-scene image, job status, `<img>` preview, download. No persistence yet (mirrors how Phase 1.3 was job-only before Phase 1.4 added storage) — Milestone C adds that.

## Verified End-to-End (real, not simulated)

- `GET /api/images/health` → `remote_ok: true`, ~13ms LAN latency.
- Real job for scene 01 (`"A lone storyteller in a dimly lit room..."`) → real 836,440-byte PNG, downloaded through the backend proxy, **visually inspected** — a person silhouetted at a window overlooking a night cityscape, matching the prompt closely.
- Real job for scene 02 (different prompt) → completed in ~4s warm (model cached from the first job).
- Invalid `scene_id` → `404`. Grepped every response for the AI Server's address/port and `/workspace` paths — clean.
- Full regression: `check_utf8`, `compileall`, `docker compose config`, frontend build, smoke test — all pass. Existing TTS/audio/export endpoints unaffected.

## Do Not Do Yet

- لا تعتبر جودة الصور معتمدة نهائياً للمنتج — لا تزال `CANDIDATE`.
- لا فيديو (Phase 3.0) قبل صور المشاهد والاستمرارية الأساسية.
- لا محرك صور جديد أو SILMA/AllTalk benchmarks.
