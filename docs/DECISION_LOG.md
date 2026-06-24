# Decision Log

## 2026-06-24 — Phase 1.2 scaffolded but BLOCKED on AI Server access

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
