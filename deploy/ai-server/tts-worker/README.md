# TTS Worker (Phase 1.2 lab)

This is the real TTS worker service for `docs/BENCHMARK_PROTOCOL.md`'s next step after the SILMA lab benchmark (`deploy/ai-server/silma-lab/`) passed. It is **isolated from the main app stack** — the root `backend/`/`frontend`/`docker-compose.yml` are never modified by this service, and the main app only ever talks to it over HTTP via `TTS_SERVICE_URL` (see Phase 1.1's `backend/app/ai_providers/tts_worker.py`).

## Status

**Code-complete, not yet run on target hardware.** This service reuses the exact generation functions already proven on the AI Server GPU in `tools/tts/silma_benchmark.py` (`instantiate_tts`, `call_silma`, reference-audio lookup), wrapped in a small FastAPI job API. It has not been built or executed on the AI Server yet — that requires SSH/Docker access to the AI Server, which was not available when this was written. Do not mark this `PASS` in `docs/BENCHMARK_PROTOCOL.md` until it has actually produced a real WAV file on the AI Server GPU.

## Scope

- One engine: SILMA (already `PASS` as an isolated lab benchmark).
- One job at a time is fine — this is a lab API, not a production queue (no Redis/Celery).
- Output files live under `data/jobs/{job_id}/` (gitignored, matches `deploy/ai-server/*/data/` in `.gitignore`).
- No ports forwarded to the public internet. This binds to the Docker host's network; keep it reachable only from the App Server over LAN, never expose it through a router/public reverse proxy. See `docs/AI_SERVER_SERVICES_ARCHITECTURE.md`.

## API

```text
GET  /health
POST /api/tts/jobs                       {"text": "...", "voice_id": null, "speed": 1.0, "format": "wav"}
GET  /api/tts/jobs/{job_id}
GET  /api/tts/jobs/{job_id}/files
GET  /api/tts/jobs/{job_id}/download/{format}
```

`POST /api/tts/jobs` returns immediately with `status: "queued"` and a `job_id`; generation runs in a background thread (SILMA's first/cold run took ~257s in the original benchmark — do not expect synchronous completion). Poll `GET /api/tts/jobs/{job_id}` until `status` is `done` or `failed`.

## Reference Voice Rule (same as the SILMA lab)

- Do not use Hamza's voice, a celebrity, presenter, or reciter voice.
- Do not download a voice from the internet.
- If `REF_AUDIO`/`REF_TEXT` are not set, the worker falls back to SILMA's bundled official benchmark sample — **this is explicitly for testing only, not an approved product voice.** Every job response that used this fallback includes `"reference_voice_note"` saying so. Set `REF_AUDIO`/`REF_TEXT` to a licensed/permitted voice before treating any output as a real product voice.

## Run (on the AI Server, GPU required)

```bash
cd deploy/ai-server/tts-worker
cp .env.example .env   # edit locally only, never commit .env
docker compose build
docker compose up -d
curl http://localhost:8851/health
```

Submit a real job:

```bash
curl -s -X POST http://localhost:8851/api/tts/jobs \
  -H "Content-Type: application/json" \
  -d '{"text": "نص عربي قصير للاختبار.", "format": "wav"}'
```

Then poll `GET /api/tts/jobs/{job_id}` and `GET /api/tts/jobs/{job_id}/files` with the returned `job_id`.

## Stop Conditions

Same as `deploy/ai-server/silma-lab/README.md`, plus:

- If the container cannot see the GPU (`nvidia-smi` fails inside it), stop — do not fall back to CPU silently.
- If a job stays `running` for more than ~10 minutes with no GPU activity, treat as `BLOCKED` and report instead of waiting indefinitely.
- Do not mark Phase 1.2 `PASS` without a real downloaded WAV file confirmed playable.
