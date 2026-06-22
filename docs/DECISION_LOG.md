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
