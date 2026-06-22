# Codex Start Implementation Prompt — Phase 0 Only

أنت Codex وتعمل كمُنفّذ فقط على مشروع AI Story Studio.

## اقرأ أولاً بالترتيب
- docs/00_START_HERE.md
- docs/AI_AGENT_RULES.md
- docs/CODER_TOOL_SOP.md
- docs/CODEX_IMPLEMENTATION_SOP.md
- docs/ARCHITECTURE.md
- docs/API_CONTRACTS.md
- docs/UI_UX_MOTION_BRIEF.md
- docs/OLLAMA_PROVIDER_SETUP.md
- docs/CURRENT_STAGE_SUMMARY.md
- docs/DECISION_LOG.md

## قواعد صارمة
- لا تعدل `.env`.
- لا تطبع أسرار.
- لا تستخدم API مدفوع.
- لا تبدأ TTS أو فيديو AI الآن.
- لا تضف DB أو Auth أو Celery.
- لا تعمل refactor كبير.
- حافظ على UTF-8.
- شغّل `python scripts/check_utf8.py` بعد التعديل.

## المهمة الحالية — Phase 0
نفذ skeleton محلي جميل وقابل للتشغيل:

### Backend
- FastAPI app.
- `GET /health`.
- Ollama adapter يقرأ:
  - `OLLAMA_BASE_URL`
  - `OLLAMA_MODEL`
- `GET /api/ai/ollama/health`.
- `POST /api/story/split-scenes`.
- استخراج JSON صالح من رد Ollama.
- حفظ project output تحت `data/projects/{project_id}/`.

### Frontend
- React + Vite + TypeScript.
- Tailwind CSS.
- Framer Motion.
- RTL Arabic UI.
- شاشة واحدة:
  - عنوان المشروع.
  - Story textarea.
  - Ollama status.
  - زر اختبار Ollama.
  - زر تقسيم القصة.
  - Scene timeline cards.
  - Output JSON panel.
  - تحذير أن الفيديو والصوت مراحل لاحقة.

### Docker
- اجعل `docker compose up --build` يعمل محلياً إن أمكن.
- لا تضف خدمات AI ثقيلة داخل compose.

## قبل التنفيذ
اعرض Plan قصير:
- الملفات التي ستنشئها.
- الملفات التي ستعدلها.
- طريقة التحقق.
ثم انتظر موافقة المستخدم.

## بعد التنفيذ
أعطني:
```text
Summary:
Files changed:
How to run:
Validation performed:
Known limitations:
Next suggested step:
```
