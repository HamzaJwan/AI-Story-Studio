# AI Server Services Architecture

## Purpose

AI Story Studio should keep production/app hosting separate from heavy AI workloads.

The Production/App Server does not need a GPU. It should run the main backend, frontend, routing, validation, and user-facing API. GPU-heavy work should run on the AI Server and be accessed through internal LAN APIs.

## Server Roles

| Server | GPU Required | Role |
| --- | --- | --- |
| Production/App Server | No | Runs the main app backend/frontend and coordinates jobs. |
| AI Server | Yes | Runs local AI services such as Ollama and future workers. |

## AI Server Services

The AI Server is the expected home for:

- `Ollama` for Phase 0 story improvement and scene splitting.
- `tts-worker` later for SILMA, XTTS/AllTalk, or Piper benchmarks.
- `ComfyUI` later for image workflows.
- `WanGP` later for video workflows.

Do not run direct GPU workloads on the Production/App Server.

SILMA has passed as an isolated AI Server Docker lab benchmark and should remain outside the App Server until a dedicated TTS worker API is designed.

## LAN API Boundaries

Use placeholders in documentation and code samples:

```env
OLLAMA_BASE_URL=http://AI_SERVER_LAN_IP:11434
TTS_SERVICE_URL=http://AI_SERVER_LAN_IP:TTS_SERVICE_PORT
COMFYUI_SERVICE_URL=http://AI_SERVER_LAN_IP:COMFYUI_SERVICE_PORT
WANGP_SERVICE_URL=http://AI_SERVER_LAN_IP:WANGP_SERVICE_PORT
```

Do not commit real LAN IPs, SSH usernames, passwords, tokens, or API keys.

## Current Phase Boundary

Phase 1.0A is planning and isolated benchmarking only:

- No backend TTS API yet.
- No frontend audio controls yet.
- No changes to the root `docker-compose.yml`.
- No public exposure of AI services.
- No production deployment changes.

## Future TTS Integration Concept

Later, after a TTS engine is selected:

1. Backend reads `TTS_SERVICE_URL` from environment.
2. Backend sends scenes or narration segments to `tts-worker`.
3. `tts-worker` creates an async job and returns `job_id`.
4. Backend polls or receives status from `tts-worker`.
5. `tts-worker` returns job status and generated audio file metadata.
6. Frontend shows an audio player only after the job is complete.

Possible future API shape:

```text
POST /api/tts/jobs
GET /api/tts/jobs/{job_id}
GET /api/tts/jobs/{job_id}/files
```

This is a planning outline only. Do not implement it during Phase 1.0A.

## Security Rules

- Keep AI services private to LAN/VPN.
- Do not expose Ollama, TTS, ComfyUI, or WanGP directly to the internet.
- Do not store SSH credentials in the repository.
- Do not hardcode real IP addresses.
- Use environment variables for service URLs.
- Add authentication and network restrictions before any production exposure.
