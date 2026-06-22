# SILMA AI Server Docker Lab

This lab is isolated from the main AI Story Studio application stack.

It is intended for a future AI Server run where Docker and NVIDIA GPU runtime are available. Do not expose this service to the internet, and do not add ports unless a later API worker is explicitly designed.

## Scope

- Benchmark SILMA TTS only.
- Use local Docker Compose in this folder.
- Write outputs under `data/benchmarks/tts/silma/`.
- Do not modify the main backend, frontend, or root `docker-compose.yml`.

## Reference Voice Rule

- Do not use Hamza's voice.
- Do not download voices from the internet.
- Do not use a real, famous, presenter, or reciter voice without clear permission.
- If SILMA does not include a clear official sample with matching reference text, the result is `NEEDS_REFERENCE`.
- Do not guess `REF_TEXT`.

## Prerequisites

Run these checks on the AI Server:

```bash
docker --version
docker compose version
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

## Setup

Use a repo clone on the AI Server, or copy this `deploy/ai-server/silma-lab/` folder together with the repository `tools/` folder.

Copy the example environment file if needed:

```bash
cp .env.example .env
```

Set only permitted local values in `.env`. Keep credentials and real server addresses out of Git.

## Run

From this folder:

```bash
docker compose build
docker compose run --rm silma-lab
```

Check outputs:

```bash
ls -lah data/benchmarks/tts/silma/
```

Expected output when the benchmark passes:

```text
data/benchmarks/tts/silma/test_audio_silma.wav
data/benchmarks/tts/silma/test_audio_silma.mp3
```

MP3 is optional for the first benchmark if WAV generation succeeds and ffmpeg conversion needs a separate fix.

## Stop Conditions

Stop and report instead of forcing the run if:

- No official/reference voice is available with clear permission and matching reference text.
- A dependency conflict appears during install.
- Download progress stalls for more than 20 minutes.
- Docker cannot see the GPU.
- No WAV is generated after a completed run.
- The build asks for credentials or an API token.

## Current Decision

This is a benchmark lab, not an application integration. The main app will later call a separate TTS worker API over LAN after the engine is selected.
