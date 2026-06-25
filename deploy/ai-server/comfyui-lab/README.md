# ComfyUI Lab (Phase 2.0 benchmark → Phase 2.1 image worker)

Isolated AI Server service, same pattern as `silma-lab`/`tts-worker`. Phase 2.0's benchmark passed (`docs/IMAGE_QUALITY_APPROVAL_CHECKLIST.md`), so as of Phase 2.1 this runs as a **persistent service** (`restart: unless-stopped`) that the main backend's `backend/app/ai_providers/image_worker.py` talks to directly over ComfyUI's own native API (`/prompt`, `/history`, `/view`) — no separate custom wrapper was needed (unlike SILMA/Piper, ComfyUI already exposes a usable job API). The frontend never talks to this service directly; only the main backend does.

## Engine choice and why

- **Engine:** ComfyUI + SDXL base 1.0 (fp16 safetensors, ~6.94GB checkpoint).
- **Why this and not Automatic1111:** community reports show ComfyUI's baseline VRAM footprint (~4.5GB) is meaningfully lower than A1111 (~7.5GB) on the same SDXL workload — important headroom on the AI Server's 8GB RTX 4060 Ti.
- **Why SDXL base and not SD 1.5 or FLUX:** SDXL is documented as running (tightly) on 8GB VRAM cards; SD 1.5 would be safer headroom but lower quality; FLUX models are larger and need more VRAM than this card has — deferred, not chosen now.
- **Model size:** ~6.94GB, well under the project's 20GB single-model stop condition.

Sources consulted (shortlist only, not a substitute for the real test below): GIGAGPU ComfyUI VRAM requirements guide, 42.uk SDXL low-VRAM ComfyUI guide, AUTOMATIC1111 GitHub discussion #11713 on 8-11GB VRAM SDXL.

## VRAM note (measured, not assumed)

The AI Server's RTX 4060 Ti has 8GB total. A pre-existing, unrelated container (`alltalk_tts-main-alltalk-tts-1`, not part of this project — do not stop it) holds ~1.9GB resident permanently, leaving **~5.86GB actually free**, confirmed via `nvidia-smi` — below the "8GB tight" baseline most SDXL/ComfyUI guides assume. Stopping `tts-worker` (Phase 1.x) does **not** free this memory (verified: it isn't the consumer), so don't bother.

To compensate for the smaller real headroom, this lab runs ComfyUI with `--lowvram` and the benchmark workflow uses 768×768 instead of 1024×1024. If this still OOMs, fall back to SD 1.5 (lower VRAM floor) — see Stop Conditions below.

## Setup

```bash
cd deploy/ai-server/comfyui-lab
cp .env.example .env
mkdir -p data/checkpoints data/output
docker compose build
```

Download the SDXL base checkpoint (run once, ~6.94GB — do not skip checking `df -h` first):

```bash
wget -O data/checkpoints/sd_xl_base_1.0.safetensors \
  https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
```

## Run

```bash
docker compose up -d
curl -s http://localhost:8188/system_stats   # confirms the server is up
```

Submit the benchmark workflow (`workflow_sdxl_txt2img.json` — one realistic cinematic prompt, 1024x1024, 20 steps):

```bash
curl -s -X POST http://localhost:8188/prompt \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": $(cat workflow_sdxl_txt2img.json)}"
```

This returns a `prompt_id`. Poll until it appears in history, then check `data/output/` for the saved PNG:

```bash
curl -s http://localhost:8188/history/<prompt_id>
ls -lh data/output/
```

## Benchmark Gate fields to record (per `docs/BENCHMARK_PROTOCOL.md`)

- engine: ComfyUI + SDXL base 1.0 fp16
- hardware: AI Server, RTX 4060 Ti, 8GB VRAM
- command: as above
- input: the bundled `workflow_sdxl_txt2img.json` prompt
- output: real PNG path + size
- cold start time (model load) vs warm generation time
- peak VRAM (`nvidia-smi` during generation)
- quality notes (technical: did it produce a real, non-corrupt 1024x1024 image — NOT a subjective art-quality judgment)
- verdict: PASS / CANDIDATE / BLOCKED / REJECTED

**Subjective image quality still needs Hamza's sign-off before any product integration** (Phase 1.x stop condition #9 — applies here too). A technical PASS here means "the pipeline produces a real image on this hardware," not "this voice/image is approved for the product."

## Stop Conditions

Same spirit as `silma-lab`/`tts-worker`:

- If the checkpoint download stalls (identical byte count over multiple 15-30s windows) the way SILMA's did in Phase 1.2, treat as `BLOCKED` (network), not a SDXL defect — retry later, don't force it.
- If `docker run --gpus all` cannot see the GPU, stop.
- If VRAM OOMs even with `tts-worker` stopped, record as `BLOCKED` and consider a smaller model (SD 1.5) as the documented fallback before abandoning Phase 2.0.
- Do not mark `PASS` without a real saved PNG confirmed non-corrupt.
