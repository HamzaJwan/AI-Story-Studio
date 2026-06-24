# Current Stage Summary

## Current Stage

**Stage:** Phase 1.3 — Connect App to TTS Worker
**Status:** Implemented and verified end-to-end with real scene audio
**Owner:** Hamza
**Executor:** Claude
**Reviewer:** Hamza

## Implemented in Phase 1.3

- `backend/app/routers/tts.py`: `POST /api/projects/{id}/tts/jobs` now derives real `text` from the stored project (`scene.narration_ar` for `mode="scene"`, all scenes joined for `mode="project"`) instead of sending an empty payload. Returns `422` for empty narration or a scene-less project.
- `backend/app/ai_providers/tts_worker.py`: new `download_file()` method proxying raw audio bytes from the worker.
- New endpoint `GET /api/tts/jobs/{job_id}/download/{format}` — proxies audio bytes + correct `Content-Type` from the worker. The browser never talks to `TTS_SERVICE_URL` directly.
- Frontend Audio panel: job status now shown in Arabic (`queued`/`running`/`done`/`failed`), and once `status: "done"`, a real `<audio>` player and a "تحميل الصوت" download link appear, both pointing at the new backend proxy endpoint. No fake audio rendered before a real file exists.
- `.env` (local only) wired with `TTS_ENABLED=true` and `TTS_SERVICE_URL` pointing at the AI Server's worker (LAN, port 8851).

## Verified end-to-end (real, not simulated)

- `GET /api/tts/health` → `remote_ok: true`, ~10ms LAN latency.
- `POST /api/projects/{id}/tts/jobs` with `mode=scene, scene_id=01` on a real saved project → real narration text flowed through → Piper generated a real WAV (435,756 bytes, 9.88s) in ~3s (warm voice cache).
- Repeated for `scene_id=02` after the AI Server's worker image was rebuilt from the *persisted* Dockerfile (not just the live-patched container) — same result, confirming the committed code path works, not just a manual patch.
- Downloaded the audio through **our own backend's** new proxy endpoint (not the worker directly) — `HTTP 200`, `audio/wav`, valid WAV verified locally.
- Full regression: `check_utf8`, backend `compileall`, frontend `npm run build` (no type errors), `smoke_phase0_workspace.py`, and all Phase 0.x endpoints (`/health`, `/api/config`, `/api/ai/ollama/health`, `scenes.json`, `export.zip`) — all still pass.

## Next Action

1. Commit and push Phase 1.3.
2. Proceed to Phase 1.4 (Project Audio Export — scene audio into `export.zip`) per the standing Controlled Autopilot instruction.

## Do Not Do Yet

- لا توليد صوت لكل المشروع كاختبار قبل أن يثبت Phase 1.4 الحاجة لذلك (المسار موجود ويعمل، لكن التركيز الحالي مشهد واحد).
- لا SILMA فعلياً (لا يزال BLOCKED بسبب الشبكة).
- لا صور، لا فيديو، لا database/auth.
