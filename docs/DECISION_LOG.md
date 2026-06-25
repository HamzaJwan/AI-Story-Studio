# Decision Log

## 2026-06-25 — Phase 2.0 PASSED: real image generated (ComfyUI + SDXL)

**Decision:** Retried the previously-stalled checkpoint download after confirming (with a corrected, valid speed test — the earlier "still blocked" recheck had a testing bug, see below) that the AI Server's network had genuinely recovered. Completed the full Benchmark Gate this time with a real generated image.

**What happened:**
- A `curl` recheck without `-L` was silently measuring only the fast HuggingFace redirect response (a few hundred bytes), not the actual file transfer — it looked like "still blocked" but wasn't a valid test. Caught this before concluding the network was still down, redid the test with `-L` and a real range request: **2.67 MB/s**, genuinely healthy.
- Restarted the `wget` checkpoint download; it completed cleanly this time (~6.5GB on disk, valid safetensors header confirmed).
- Started `comfyui-lab`, confirmed GPU visible (`cuda:0 NVIDIA GeForce RTX 4060 Ti`), submitted the bundled `workflow_sdxl_txt2img.json` (768×768, 20 steps).
- Result: `status: success` in ~14.7s (cold run, including model load). Peak VRAM 6995 MiB used / 812 MiB free — tight, but no OOM. Output `benchmark_phase2_00001_.png`, 768×768 RGB, 693,857 bytes.
- **Downloaded the actual image and looked at it directly** (not just checked statistics): a coherent, real scene — a person sitting by a window at night with warm light — matching the input prompt closely, no corruption or artifacts.

**Impact:**
- Phase 2.0 is `PASS` technically: the pipeline produces a real, valid image on this hardware, end to end.
- **Not the same as product approval.** Per stop condition #9 ("تحتاج تقييم جودة بشري لصوت/صورة/فيديو قبل اعتباره PASS"), Hamza still needs to look at and approve the actual image quality before Phase 2.1 (Image Worker Bridge) or any frontend image UI work begins. This decision only confirms the pipeline works, not that the visual quality is approved for the product.
- VRAM headroom is genuinely tight (812 MiB free at peak) — any future workflow change (higher resolution, refiner pass, batch>1) needs to be tested for OOM risk, not assumed safe.

---

## 2026-06-24 — Phase 2.0 scaffolded but BLOCKED on AI Server network (first attempt)

**Decision:** Write the ComfyUI + SDXL image benchmark lab fully (code, workflow, docs) per the standing autopilot instruction to proceed past audio into images, but do not claim any PASS/CANDIDATE without a real generated PNG.

**Engine choice (research, not guesswork):** ComfyUI + SDXL base 1.0 fp16 (~6.94GB, under the 20GB stop-condition). Web research (cited in `deploy/ai-server/comfyui-lab/README.md`) shows ComfyUI's baseline VRAM footprint is meaningfully lower than Automatic1111's on the same SDXL workload, and SDXL is documented as workable (tightly) on 8GB cards, while FLUX needs more VRAM than this card has. This is a shortlist per `docs/BENCHMARK_PROTOCOL.md`, not a final decision — only a real successful generation makes it one.

**Real constraint discovered:** `nvidia-smi` showed only ~5.86GB free, not the full 8GB — a pre-existing, unrelated container (`alltalk_tts-main-alltalk-tts-1`, not part of this project) holds ~1.9GB permanently and was deliberately left untouched (not ours to manage). Compensated with `--lowvram` and a 768×768 benchmark resolution instead of 1024×1024.

**What happened:** Started the Docker image build and the ~6.94GB checkpoint download in parallel. Both stalled — checkpoint download speed dropped from ~123 KB/s to under 1 KB/s sustained over 20+ minutes (confirmed via repeated byte-count checks, same diagnostic method used for SILMA). This is the **second** time tonight the AI Server's network has stalled a large download (SILMA's ~2GB model earlier, now this). Killed the dead `wget` and removed the useless partial file. Could not kill the build's root-owned `apt-get install` subprocess without sudo — left it running; it's a few small packages, not a resource concern.

**Impact:**
- Phase 2.0 is `BLOCKED` (network), not `PASS`/`CANDIDATE`/`REJECTED` — no image has been generated. The lab code itself is complete and ready to retry the moment the network is healthy.
- This is now a pattern (2 of 2 large downloads attempted on the AI Server tonight have stalled) worth Hamza checking independently — likely the AI Server's actual internet link, not anything about SILMA or SDXL specifically.
- Not proceeding to Phase 2.1 (Image Worker Bridge) or any UI work — nothing to bridge yet without a real generated image.

---

## 2026-06-24 — Phase 1.4: Project Audio Export (real audio in export.zip)

**Decision:** Generate audio for every scene in a project, persist metadata, and add it to `export.zip` — without breaking the existing ZIP shape for projects with no audio.

**What changed:**
- New `POST /api/projects/{project_id}/tts/generate-all`: sequential per-scene jobs against the real worker, each polled to completion, downloaded, and saved to `data/projects/{project_id}/audio/scene_{id}.wav`.
- `Scene` schema gained optional audio metadata fields (additive — doesn't break existing stored projects missing them).
- `build_export_zip()` now includes per-scene WAVs plus a `final_story.wav` (raw WAV concatenation via stdlib `wave`, since the backend image has no ffmpeg). Documented as a known limitation in the exported `metadata.json` rather than silently shipping something that looks like a finished MP3.
- Frontend's existing "توليد صوت للمشروع" button now calls this batch endpoint instead of the old single concatenated-text job (which generated audio but never saved or exposed it for export) — a behavior upgrade to the same button, not a new UI element.

**Bug found and fixed before commit:** `scenes_export()` called `Scene.model_dump()` without `mode="json"`, so once a scene had `audio_generated_at` (a `datetime`) set, `export.zip` crashed with a 500 (`TypeError: Object of type datetime is not JSON serializable`). Caught by testing against the real 6-scene project before considering this done, fixed, retested.

**Evidence:**
- Real 6-scene project → `generate-all` → `{"generated": ["01".."06"], "failed": []}`, each scene's audio metadata persisted.
- Downloaded `export.zip` → 6 real WAVs + `final_story.wav` (2,050,092 bytes, verified valid WAV, 46.49s).
- Confirmed `export.zip` for a zero-scene project still returns `200` (no regression).
- Full regression suite passes.

**Impact:** Phase 1.4 is `PASS`. Per the standing Controlled Autopilot instruction, the next step is Phase 2.0 (Image Benchmark Lab) — pausing briefly to scope that properly (new engine, new AI Server service, Benchmark Gate) rather than rushing in.

---

## 2026-06-24 — Phase 1.3: Connect App to TTS Worker (real audio end-to-end)

**Decision:** Wire the existing Audio Bridge (Phase 1.1) to the real worker (Phase 1.2) for a single scene first, per the project's own rule ("لا توليد كل المشروع قبل نجاح مشهد واحد").

**What changed:**
- `backend/app/routers/tts.py`: job creation now reads the real scene/project narration text from storage and sends it to the worker (previously sent no `text` at all — a gap Phase 1.2's docs explicitly flagged for this phase).
- New `GET /api/tts/jobs/{job_id}/download/{format}` on our own backend, proxying the worker's audio bytes — the browser/frontend never talks to `TTS_SERVICE_URL` directly, preserving the LAN-only boundary from `docs/AI_SERVER_SERVICES_ARCHITECTURE.md`.
- Frontend Audio panel renders a real `<audio>` player + download link only after `status: "done"`, built from `${API_BASE_URL}/api/tts/jobs/{id}/download/{format}` — no fake success.

**Evidence:**
- Real saved project (`cb005fd1...`), scene `01` narration ("في ليلة هادئة...") → real job → real Piper WAV (435,756 bytes, 9.88s) in ~3s warm.
- Repeated for scene `02` *after* rebuilding the AI Server's worker image from the corrected, persisted Dockerfile (not the earlier live-patched container) — confirms the committed code actually works, not just a manual fix.
- Downloaded both ways were verified: backend's own connectivity test (`remote_ok: true`, ~10ms LAN) and a full WAV download through the new backend proxy endpoint (valid headers, valid WAV content).
- Full regression suite (`check_utf8`, `compileall`, `npm run build`, `smoke_phase0_workspace.py`, all Phase 0.x endpoints) passes — nothing broke.

**Impact:** Phase 1.3 is implemented and verified. Proceeding to Phase 1.4 (scene audio into `export.zip`) automatically per the Controlled Autopilot instruction — no stop condition was hit.

---

## 2026-06-24 — Phase 1.2 PASSED on AI Server via Piper; SILMA BLOCKED on network

**Decision:** SSH access to the AI Server was resolved (key-based alias `ai-story-server`, no password ever used). Built and ran `deploy/ai-server/tts-worker/` for real. SILMA's model download stalled twice on HuggingFace's CDN — diagnosed as a real network condition, not a code defect — so pivoted to Piper as the fallback engine, per the project's own rule ("SILMA blocked → جرّب Piper").

**Evidence (no claim without real output):**
- GPU confirmed inside the container: `nvidia-smi` → RTX 4060 Ti, 8188 MiB.
- SILMA stall diagnosis: identical byte count on the partial download across multiple 15-30s windows (confirmed twice, after a container restart), TCP retransmission counters confirmed via `/proc/net/tcp`, and a direct `curl` range request to the *same* CDN URL succeeded at 200-530 KB/s in isolation — the path works, a single long-lived download to it does not, reliably, tonight.
- Piper produced two real WAV files: short text (221,740 bytes, 5.03s, cold run ~6 min including a ~63MB voice download under degraded network) and a longer sentence with punctuation and a number (756,268 bytes, 17.15s, warm run **~3.8s**). Both verified as real non-silent audio (max amplitude 32767, RMS ≈ 4051/≈ similar, ~98.6% non-zero samples) and downloaded successfully via `GET /api/tts/jobs/{id}/download/wav`.
- Voice used: `ar_JO-kareem-medium` from `rhasspy/piper-voices` (HF repo tagged `license:mit`; voice card shows dataset from an open community Arabic TTS training repo, finetuned from the English `lessac` voice) — not Hamza's voice, not a celebrity, not a real-person clone without consent.
- Along the way, fixed a self-inflicted Docker layer-caching mistake: adding `piper-tts` to the *same* RUN instruction as the heavy SILMA/torch install invalidated that layer's cache and forced a ~95-minute reinstall; split it into its own RUN layer so the expensive layer stays cached for future builds.
- Resolved Phase 0.5's "pending verification" hardware fields using the same SSH access (exact VRAM, disk space, actual running Docker services) — see `docs/HARDWARE_PROFILE.md`. Also discovered an already-running `alltalk_tts` container (port 7851) on the AI Server, untouched, noted for a future real benchmark.

**Impact:**
- Phase 1.2 is `PASS` in `docs/ROADMAP.md` and `docs/TTS_ENGINE_BENCHMARK_MATRIX.md` (Piper). SILMA stays `BLOCKED` (network), code kept behind `ENGINE=silma` for a later retry — not deleted, not marked `REJECTED` (the engine itself isn't the problem).
- `TTS_ENGINE_BENCHMARK_MATRIX.md` updated with full Benchmark Gate fields (engine, version, hardware, command, output, timing, quality notes, limitations, verdict) for both attempts.
- Proceeding directly to Phase 1.3 (Connect App to TTS Worker) per the standing Controlled Autopilot instruction — no new stop condition was hit.

---

## 2026-06-24 — Phase 1.2 scaffolded but BLOCKED on AI Server access (superseded above)

**Decision:** كتابة كود TTS Worker (`deploy/ai-server/tts-worker/`) كاملاً الآن، بدون تشغيله، وتسجيل الحالة كـ `BLOCKED` بدل `DONE` أو `PASS`.

**Reason:**
- المرحلة المطلوبة (Phase 1.2) تحتاج Docker + GPU فعلي على AI Server.
- لا يوجد SSH key/session متاحة. كلمة مرور SSH أُرسلت سابقاً في المحادثة، لكن harness الأمان يمنع تمرير أي password داخل أوامر shell (sshpass أو غيره) بشكل قاطع — هذا حاجز تقني صلب، ليس قرار حذر قابلاً للتجاوز بالاجتهاد.
- كتابة الكود الآن (بإعادة استخدام دوال `tools/tts/silma_benchmark.py` المُثبَتة فعلياً على GPU سابقاً) يجهّز المشروع للتشغيل الفوري بمجرد توفر الوصول، بدون انتظار جلسة جديدة لإعادة تصميم نفس الشيء.

**Impact:**
- Phase 1.2 مسجَّلة `BLOCKED` في `docs/ROADMAP.md`، لا `DONE`.
- كل من Phase 1.3, 1.4, 2.0, 2.1, 3.0, 3.1, 3.2 محجوبة بنفس الحاجز لأنها تعتمد على AI Server.
- الحل الوحيد الدائم: حمزة يضيف SSH key (بدون password) إلى AI Server، أو يشغّل worker بنفسه يدوياً ويؤكد النتيجة.
- لا PASS في `docs/BENCHMARK_PROTOCOL.md` لهذا الـ worker حتى يُنتِج WAV حقيقي مؤكَّد على العتاد الفعلي.

---

## 2026-06-24 — Start Phase 1.1: Audio Bridge MVP

**Decision:** ننتقل إلى Phase 1.1 بعد Phase 0.5، كجسر اتصال فقط — لا تشغيل أي TTS engine داخل التطبيق.

**Reason:**
- Phase 0.5 وضعت Benchmark Gate رسمي، ولم يصدر `PASS` بعد لأي TTS worker فعلي (SILMA لا يزال isolated lab، AllTalk لا يزال candidate).
- لكن المنتج يحتاج البنية الجاهزة (connector + UI state) الآن، بحيث لو نجح worker لاحقاً على AI Server، التكامل يكون فورياً بدون إعادة هيكلة.
- هذا لا يكسر قاعدة Phase 0.5 لأن لا engine حقيقي يُشغَّل أو يُدمَج — فقط استجابة `configured: false` افتراضية.

**Scope:**
- Backend: `TTS_ENABLED`/`TTS_SERVICE_URL`/`TTS_TIMEOUT_SECONDS` (افتراضياً معطّلة)، `TtsWorkerClient`، 3 endpoints جديدة (`/api/tts/health`, `POST .../tts/jobs`, `GET /api/tts/jobs/{id}`).
- Frontend: لوحة "استوديو الصوت" (تجريبي) بعد المشاهد، فحص حالة + توليد + تحديث job، بدون audio وهمي.
- `scripts/smoke_phase0_workspace.py` لحماية CRUD/export.zip من الانكسار الصامت.

**What Phase 1.1 is NOT:**
- لا تشغيل SILMA/AllTalk/أي TTS فعلي.
- لا GPU، لا تحميل موديلات.
- لا صور، لا فيديو، لا database/auth/Redis/Celery.
- لا فتح Phase 1.1 الكامل (pipeline صوت متزامن) — هذا جسر اتصال أولي فقط.

---

## 2026-06-24 — Start Phase 0.4: Story Package Export

**Decision:** ننتقل إلى Phase 0.4 بعد إتمام Phase 0.3 وقبل أي عمل على TTS.

**Reason:**
- Phase 0.3 منجزة ومدفوعة وتعمل.
- المشروع يحتاج صيغة أرشفة/نقل واحدة (ZIP) تجمع القصة والمشاهد والبيانات الوصفية قبل أي عمل على الصوت.
- لا حاجة لأي مكتبة جديدة — zipfile/io من المكتبة القياسية تكفي.

**Scope:**
- Backend: endpoint جديد واحد `GET /api/projects/{project_id}/export.zip`.
- Frontend: زر تحميل واحد فقط، يعتمد على وجود project_id محفوظ.
- لا تغيير في أي endpoint أو schema قديم.

**What Phase 0.4 is NOT:**
- لا TTS، لا SILMA integration، لا AllTalk integration.
- لا صور، لا فيديو، لا ComfyUI.
- لا refactor لـ App.tsx، لا مكتبات جديدة.

---

## 2026-06-24 — Start Phase 0.3: Scene Editing UX Polish (frontend-only)

**Decision:** ننتقل إلى Phase 0.3 بعد إتمام Phase 0.2 وقبل أي تطوير TTS.

**Reason:**
- Phase 0.2 منجزة ومدفوعة وتعمل.
- TTS لا تزال تجارب isolated labs (SILMA/AllTalk) — لم يُتخذ قرار بعد.
- تحسين UX تعديل المشاهد يضيف قيمة فورية للمستخدم.

**Scope:**
- Frontend-only — لا تغيير في backend أو API contracts.
- Collapsed/expanded scene cards.
- أزرار: ↑ ↓ نسخ إضافة حذف لكل مشهد.
- Validation warnings داخل الكرت.
- Scene stats bar.
- Download scenes.json من النسخة المعدلة + confirm عند وجود تحذيرات.

**What Phase 0.3 is NOT:**
- لا TTS، لا SILMA integration، لا AllTalk integration.
- لا صور، لا فيديو، لا ComfyUI.
- لا refactor جذري، لا تغيير API.

---

## 2026-06-22 — Start with Benchmark, not full video

**Decision:** نبدأ بـ Phase 0 + Phase 1، ونؤجل فيديو AI الكامل.

**Reason:**
- الفيديو المحلي على 8GB VRAM ما زال تجريبياً.
- الصوت والسيناريو أكثر قيمة الآن.
- الصور الثابتة + مونتاج ستكون أقرب لجودة نشر محترمة.

**Impact:**
- MVP أخف.
- Codex لا يغرق في Wan2.1.
- نثبت القيمة قبل التوسع.

---

## 2026-06-22 — Use Adapter Pattern for AI

**Decision:** لا نربط التطبيق مباشرة بـ Ollama فقط.

**Reason:**
لاحقاً يمكن إضافة OpenAI/Gemini/Anthropic/Local providers بدون إعادة بناء.

---

## 2026-06-22 — React/FastAPI instead of Gradio for product UI

**Decision:** نستخدم React + FastAPI للواجهة الرسمية، رغم أن Gradio أسرع.

**Reason:**
المستخدم يريد تصميم جميل وعصري قريب من ADC Portal، لا مجرد demo.

---

## 2026-06-22 — Implement Phase 0.1 with local Ollama only

**Decision:** Phase 0.1 يستخدم FastAPI + React/Vite + Ollama عبر `.env` فقط.

**Reason:**
- المطلوب إثبات Improve Story وSplit Scenes قبل أي صوت أو صور أو فيديو.
- التخزين file-based يكفي للمرحلة الحالية.
- CORS يقرأ من env ولا يستخدم wildcard.

**Impact:**
- لا DB/Auth/Redis/Celery.
- لا OpenAI/Gemini API.
- `scenes.json` هو مخرج Phase 0.1 الأساسي.

---

## 2026-06-24 — SILMA benchmark passed as isolated AI Server lab

**Decision:** SILMA TTS passed the AI Server GPU benchmark, but remains isolated from the main app.

**Reason:**
- SILMA generated both WAV and MP3 on the AI Server GPU/CUDA path.
- First generation completed in `256.95s`.
- First bootstrap/build was heavy due to PyPI/HuggingFace dependency downloads.
- The successful benchmark used SILMA's bundled official Arabic reference sample for testing only.

**Impact:**
- SILMA stays in `deploy/ai-server/silma-lab/`.
- No backend/frontend TTS integration yet.
- Future product integration should use a separate LAN `tts-worker` API.

---

## 2026-06-24 — Start Phase 0.2 Project Workspace

**Decision:** Return to the product and implement a local Project Workspace before expanding TTS.

**Reason:**
- Phase 0.1 is useful, but users need saved projects and editable scenes.
- SILMA passed as a benchmark, but TTS remains isolated and should not block workspace progress.

**Impact:**
- Add JSON-file project storage under `data/projects/`.
- Add project CRUD endpoints.
- Add editable scene cards and `scenes.json` export after edits.
- No TTS/audio/image/video integration in Phase 0.2.

---

## 2026-06-24 — Phase 0.2 passed manual review

**Decision:** Phase 0.2 Project Workspace is accepted as implemented and manually verified.

**Reason:**
- Creating a new project works.
- Saving and loading local projects works.
- Editing generated scenes works.
- Saving scene edits works.
- Downloading `scenes.json` after edits works.
- Exported scenes include valid narration, visual prompt, and duration.

**Impact:**
- Phase 0.2 is ready as the current product baseline.
- TTS/SILMA/AllTalk remain isolated labs and are not part of the app UI.
- Next step is Phase 0.3 — Scene Editing UX Polish before any TTS UI.

---

## 2026-06-25 — Align roadmap with media-generation vision

**Decision:** Treat Phase 2.0 as a technical image benchmark PASS, but require Hamza's product-quality sign-off and a small UI/status sync before Phase 2.1 starts.

**Reason:**
- The current app is no longer only a story-to-scenes tool; it now has a proven audio path and a technically proven image benchmark.
- Hamza's new direction requires planning for image continuity, long-story batching, style presets, a separate Image Studio, genre-aware narration, and future video assembly.
- Community and research patterns show that prompt-only scene generation is not enough for recurring characters, stable locations, or object/color consistency. Continuity needs story/character/location/object bibles plus benchmarked reference workflows.

**Impact:**
- `docs/ROADMAP.md` now separates Phase 2.1 image worker bridge, Phase 2.2 scene image generation, Phase 2.3 continuity foundation, Phase 2.4 style presets, Phase 2.5 Image Studio, Phase 2.6 long-story batching, and Phase 3.x video work.
- New strategy docs describe media expansion, image continuity, and unified job progress.
- Recommendation is `APPROVED WITH FIXES`: close the quality sign-off and small UI/status mismatch before implementation resumes.

---

## 2026-06-25 — Choose Phase 1.5 Audio UX Polish before image bridge

**Decision:** The next execution phase should be `Phase 1.5 — Audio UX Polish`, not Phase 2.1.

**Reason:**
- The audio backend and worker path are already proven, including real scene audio and project audio export.
- Hamza's current product test shows the user still has to rely on ZIP inspection to find audio files.
- The app has a single-job player, but lacks a complete product workflow for saved per-scene audio, full-story playback, voice selection, language selection, and clear progress.
- Phase 2.1 image work still depends on image-quality approval and continuity planning.

**Impact:**
- Phase 1.5 should improve UX around existing audio capabilities without adding a new TTS engine.
- All audio must remain behind backend proxy endpoints; the browser must not call the AI Server directly.
- Image/video work remains paused until Audio UX is polished and Hamza approves image quality.

---

## 2026-06-25 — Add subtitles as a future video feature

**Decision:** Treat subtitles as a first-class future video layer, not as an afterthought.

**Reason:**
- The product already has structured scene narration, durations, and generated audio, which are natural inputs for subtitle timing.
- Arabic subtitles are important for story videos and social sharing.
- Sidecar subtitles (`.srt`/`.vtt`) are safer to implement before burned-in MP4 captions because they can be inspected and edited.
- Burned-in captions should come later when the video assembly/export path exists.

**Impact:**
- Phase 3.0 should include subtitle sidecar export based on scene narration and timing.
- Phase 3.1 should include optional burned-in subtitles in MP4.
- Subtitles must support Arabic RTL/UTF-8 and optionally English if translation exists.
- Do not implement subtitles now; Phase 1.5 Audio UX remains the next execution step.
