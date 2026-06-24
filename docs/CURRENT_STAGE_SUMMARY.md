# Current Stage Summary

## Current Stage

**Stage:** Phase 1.3 — Connect App to TTS Worker
**Status:** Starting — Phase 1.2 passed with real verified audio on AI Server
**Owner:** Hamza
**Executor:** Claude
**Reviewer:** Hamza

## Phase 1.2 Result (closed out)

**PASS** via Piper, **BLOCKED** via SILMA (network, not code) — full detail in `docs/TTS_ENGINE_BENCHMARK_MATRIX.md`.

- SSH access to the AI Server was resolved with a key-based alias (`ssh ai-story-server`), no password ever touched by the agent.
- `deploy/ai-server/tts-worker/` built and ran on the real AI Server (RTX 4060 Ti, 8188 MiB VRAM confirmed). The repo checkout there was fast-forwarded to the latest `main`.
- SILMA's ~2GB model download stalled twice on HuggingFace's CDN (confirmed via byte-for-byte stagnation and TCP retransmissions) — a real network condition on the AI Server that night, not a SILMA defect. Kept the code behind `ENGINE=silma` for a future retry.
- Pivoted to Piper (`ENGINE=piper`, now the default) per the project's own fallback rule. Produced two real WAV files (short + long text with punctuation/numbers), both verified as genuine non-silent audio (waveform statistics), both downloadable via the worker's `/download/wav` endpoint. Warm-run latency ~3.8s.
- Fixed a packaging mistake along the way: `piper-tts` was first added to the same Docker layer as the heavy SILMA/torch install, invalidating that cache and forcing a ~95-minute reinstall; split into its own layer so the expensive layer stays cached.
- Also resolved Phase 0.5's "pending verification" hardware fields (exact VRAM, disk space, running Docker services) using the same SSH access — `docs/HARDWARE_PROFILE.md` updated.
- Discovered an already-running `alltalk_tts` container (`erew123/alltalk_tts:cuda`, port 7851) on the AI Server — not touched, noted as a future real-benchmark candidate.

## Current Goal (Phase 1.3)

ربط Audio panel الموجود (Phase 1.1) بـ `tts-worker` الحقيقي (Phase 1.2) لمشهد واحد فقط أولاً:
- توسيع `backend/app/routers/tts.py` ليرسل نص المشهد الفعلي (`narration_ar`) كحقل `text` للـ worker.
- زر "توليد صوت للمشهد الأول" في الواجهة يستدعي job حقيقياً، يعرض job_id/status حقيقي.
- عند اكتمال الملف فعلياً، تظهر `<audio>` حقيقية قابلة للتشغيل والتحميل.
- لا توليد لكل المشروع قبل نجاح مشهد واحد. لا fake audio.

## Do Not Do Yet

- لا تشغيل SILMA فعلياً حتى تتحسن الشبكة (أو قرار بمحاولة جديدة).
- لا اختبار AllTalk الآن (موجود لكن غير ضمن نطاق هذه المرحلة).
- لا صور، لا فيديو، لا database/auth.
