# Current Stage Summary

## Current Stage

**Stage:** Phase 1.2 — TTS Worker Lab API
**Status:** 🟡 BLOCKED — code complete and reviewed locally, never built/run on real hardware
**Owner:** Hamza
**Executor:** Claude
**Reviewer:** Hamza

## Current Goal

تشغيل TTS Worker حقيقي (SILMA) منفصل عن backend الرئيسي، في `deploy/ai-server/tts-worker/`، بنفس Dockerfile/recipe الناجح في `deploy/ai-server/silma-lab/`، يعرض `GET /health`, `POST /api/tts/jobs`, `GET /api/tts/jobs/{id}`, `GET /api/tts/jobs/{id}/files`.

## Why This Is Blocked

كل المراحل من 1.2 إلى 3.2 في الرودماب تحتاج تنفيذ Docker فعلي على AI Server. لا يوجد SSH key أو session متاحة حالياً، وتمرير كلمة المرور التي أُرسلت سابقاً في المحادثة داخل أي أمر sh ممنوع من harness الأمان نفسه (credential-leakage guard) — هذا ليس قرار حذر بل عدم قدرة فعلية على التنفيذ التلقائي.

**ما لا يمكن إثباته بدون AI Server:** أن الـ container يرى GPU فعلياً، وأن SILMA تنتج WAV حقيقي عبر الـ worker الجديد (لا فقط عبر السكربت القديم في `silma-lab`).

## Implemented Locally (code-complete, unverified on target hardware)

- `deploy/ai-server/tts-worker/Dockerfile` — نفس recipe `silma-lab` الناجح + fastapi/uvicorn/pydantic.
- `deploy/ai-server/tts-worker/app/jobs.py` — يعيد استخدام دوال `tools/tts/silma_benchmark.py` المُثبَتة فعلياً (لا منطق هش جديد)، job في thread خلفي (لا Redis/Celery)، job state محفوظ كـ JSON تحت `data/jobs/{id}/`.
- `deploy/ai-server/tts-worker/app/main.py` — FastAPI routes مطابقة لـ TTS Worker Contract في `docs/API_CONTRACTS.md`.
- `deploy/ai-server/tts-worker/docker-compose.yml`, `.env.example`, `README.md` — يوثّق التشغيل، قاعدة الصوت المرجعي، وStop Conditions.
- Python syntax مفحوص محلياً (`py_compile`)، `docker compose config` على الملف الجديد نجح. **لم يُبنَ الـ image، لم يُشغَّل، لم يُنتَج أي WAV حقيقي بعد.**

## Next Action

1. حمزة يوفّر طريقة وصول آمنة لـ AI Server (الأفضل: SSH key بدون password — أضِف مفتاحاً عاماً إلى `~/.ssh/authorized_keys` على السيرفر، بدون أي تعديل آخر).
2. بعد الوصول: بناء الصورة فعلياً، تشغيل job حقيقي، تحميل WAV والتأكد أنه يُشغَّل.
3. فقط بعد ذلك يُسجَّل `PASS` في `docs/BENCHMARK_PROTOCOL.md` ويُعتبر Phase 1.2 منجزة.

## Do Not Do Yet

- لا تسجيل PASS بدون WAV حقيقي محفوظ ومُشغَّل فعلياً.
- لا Phase 1.3/1.4/2.0/3.0 قبل حل هذا الحاجز.
- لا صور، لا فيديو، لا database/auth.
