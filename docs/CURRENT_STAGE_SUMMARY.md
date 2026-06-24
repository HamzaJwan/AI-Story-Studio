# Current Stage Summary

## Current Stage

**Stage:** Phase 2.0 — Image Benchmark Lab
**Status:** 🟡 BLOCKED — lab code complete, checkpoint download stalled on AI Server network
**Owner:** Hamza
**Executor:** Claude
**Reviewer:** Hamza

## What happened

Phase 1.x (audio) finished completely successfully — TTS worker running, real audio for scenes and full project export, all pushed. Per the standing autopilot instruction, moved into Phase 2.0 (Image Benchmark Lab).

- Researched engine choice (web search, not guesswork): ComfyUI + SDXL base 1.0 fp16 (~6.94GB, well under the 20GB stop-condition), chosen over Automatic1111 (heavier baseline VRAM) and FLUX (needs more VRAM than available).
- Discovered the AI Server's *actually* free VRAM is ~5.86GB, not the full 8GB — a pre-existing, unrelated container (`alltalk_tts`, not part of this project, not touched) holds ~1.9GB permanently. Compensated by adding `--lowvram` and dropping the benchmark resolution to 768×768.
- Scaffolded `deploy/ai-server/comfyui-lab/` (Dockerfile, docker-compose.yml, a real ComfyUI API workflow JSON, README with Benchmark Gate fields and stop conditions) — mirrors the `tts-worker` pattern.
- Fixed a gitignore gap before any large file existed: the lab's checkpoint/output directories didn't match the existing `deploy/ai-server/*/data/` ignore pattern; renamed to align before downloading anything.
- Started the build and the ~6.94GB checkpoint download in parallel. **Both stalled** — download speed dropped from ~123 KB/s to under 1 KB/s sustained over 20+ minutes, the same network condition that blocked SILMA's model download earlier this session.
- Killed the stalled `wget` (confirmed dead) and deleted the useless partial file. Could not force-kill the build's root-owned `apt-get install` subprocess without sudo — left it; it's small (a few MB of packages) and harmless to leave running unattended.

**Note:** this is the second time tonight the AI Server's network has stalled a large download (SILMA's ~2GB model, now SDXL's ~7GB checkpoint). Worth Hamza checking the AI Server's actual internet connection/ISP independently of any specific phase.

## Next Action

1. Retry the checkpoint download when the AI Server's network is confirmed healthy (a simple `curl` speed test to the same HuggingFace URL is enough to check before retrying — no need to redo the research).
2. Until then, Phase 2.0 stays `BLOCKED`, not `PASS` — no image has been generated, no claim is made that one has.

## Do Not Do Yet

- لا تكرار محاولة تحميل checkpoint بدون تأكد أن الشبكة تحسّنت (فحص سريع كافٍ، لا حاجة لإعادة كل البحث).
- لا Image Worker Bridge (Phase 2.1) ولا UI صور قبل نجاح هذا الـ benchmark فعلياً بصورة حقيقية.
- لا فيديو حتى تُحسم الصور.
