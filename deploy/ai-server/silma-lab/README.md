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

For the AI Server benchmark path that successfully passed, build from the repository root with host networking:

```bash
docker build --network=host --progress=plain -t ai-story-silma-lab -f deploy/ai-server/silma-lab/Dockerfile .
```

After the image exists, run only the benchmark without rebuilding:

```bash
docker run --rm --gpus all \
  -e SILMA_OUTPUT_DIR=/workspace/data/benchmarks/tts/silma \
  -e SILMA_SPEED=1.0 \
  -v "$PWD/deploy/ai-server/silma-lab/data:/workspace/data" \
  -v "$PWD/tools:/workspace/tools" \
  -w /workspace \
  ai-story-silma-lab \
  python tools/tts/silma_benchmark.py
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

Successful AI Server benchmark outputs were written under:

```text
deploy/ai-server/silma-lab/data/benchmarks/tts/silma/
```

The successful benchmark used SILMA's bundled official Arabic reference sample for testing only:

```text
official_silma_ar.ref.24k.wav
```

Do not treat the benchmark reference sample as a product voice.

## Stop Conditions

Stop and report instead of forcing the run if:

- No official/reference voice is available with clear permission and matching reference text.
- A dependency conflict appears during install.
- Download progress stalls for more than 20 minutes.
- Docker cannot see the GPU.
- No WAV is generated after a completed run.
- The build asks for credentials or an API token.

## Current Decision

This is a passed benchmark lab, not an application integration. SILMA generated WAV and MP3 on the AI Server GPU, but first bootstrap/build cost is heavy. The main app will later call a separate TTS worker API over LAN after the engine is selected.
