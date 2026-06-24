# Decision Log

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
