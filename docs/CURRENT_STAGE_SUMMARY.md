# Current Stage Summary

## Current Stage

**Stage:** Phase 1.1 — Audio Bridge MVP
**Status:** Implemented locally — pending Hamza verification and push approval
**Owner:** Hamza
**Executor:** Claude
**Reviewer:** Hamza

## Current Goal

إضافة طبقة صوت أولية (جسر اتصال فقط) داخل المنتج، بدون تشغيل أي موديل صوت داخل التطبيق:
- Backend connector لـ TTS Worker خارجي عبر `TTS_SERVICE_URL` / `TTS_ENABLED`.
- إذا الخدمة غير مفعّلة، endpoints وواجهة المستخدم تقول ذلك بوضوح بدون crash وبدون صوت وهمي.
- إذا الخدمة مفعّلة لاحقاً (بعد Benchmark Gate = PASS)، التطبيق جاهز للتكامل بدون تغيير بنية الكود.

## Implemented in Phase 1.1

- `backend/app/config.py`: `TTS_ENABLED` (default `false`), `TTS_SERVICE_URL`, `TTS_TIMEOUT_SECONDS`، وخاصية `tts_configured`.
- `backend/app/ai_providers/tts_worker.py`: `TtsWorkerClient` — health check + proxy لإنشاء/جلب job.
- `backend/app/routers/tts.py`:
  - `GET /api/tts/health` — يرجع 200 دائماً مع `configured: false/true`.
  - `POST /api/projects/{project_id}/tts/jobs` — 503 إذا غير مفعّل، 404 لمشروع/مشهد غير موجود، 502 إذا تعذّر الوصول للـ worker.
  - `GET /api/tts/jobs/{job_id}` — نفس منطق 503/502.
- Frontend: قسم "استوديو الصوت" (badge "تجريبي") بعد المشاهد — فحص الحالة تلقائياً عند التحميل، أزرار توليد صوت للمشهد الأول/للمشروع معطّلة إذا الخدمة غير مفعّلة، بطاقة job_id/status مع زر تحديث، بدون أي audio player وهمي.
- `scripts/smoke_phase0_workspace.py` — فحص سريع لـ health/projects CRUD/scenes.json/export.zip.
- لا SILMA، لا AllTalk، لا ComfyUI، لا WanGP، لا GPU، لا تحميل موديلات.

## Next Action

1. حمزة يشغّل الفحوصات ويتحقق يدوياً من ظهور لوحة الصوت وحالتها (غير مفعّلة بدون env).
2. حمزة يوافق على commit وpush.

## Do Not Do Yet

- لا تشغيل فعلي لـ TTS Worker — لم يُبنَ بعد، ولم يمرّ بـ Benchmark Gate.
- لا صور، لا فيديو، لا ComfyUI، لا WanGP.
- لا production deploy، لا database/auth.
