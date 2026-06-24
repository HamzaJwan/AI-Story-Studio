# Current Stage Summary

## Current Stage

**Stage:** Phase 0.4 — Story Package Export
**Status:** Implemented locally — pending Hamza verification and push approval
**Owner:** Hamza
**Executor:** Claude
**Reviewer:** Hamza

## Current Goal

إضافة تصدير حزمة مشروع كاملة كملف ZIP واحد:
- story.txt (original_story)
- improved_story.txt (improved_story)
- scenes.json (مطابق لـ GET /api/projects/{project_id}/scenes.json)
- metadata.json (project_id, title, created_at, updated_at, scene_count, total_duration_seconds, exported_at, app, phase)

Phase 0.4 فقط: endpoint جديد + زر تحميل واحد في الواجهة — لا TTS، لا صور، لا فيديو، لا dependencies جديدة.

## Implemented in Phase 0.4

- `ProjectStorage.build_export_zip()` يبني ZIP في الذاكرة (io.BytesIO + zipfile) من المكتبة القياسية فقط.
- `GET /api/projects/{project_id}/export.zip` — يرجع ZIP صالح أو 404 بنفس نمط الأخطاء الحالي.
- زر "تحميل حزمة المشروع ZIP" في الواجهة، فعّال فقط بعد حفظ المشروع (وجود project_id).
- لا تغيير في endpoints أو schemas القديمة.
- لا تغيير في تصميم الواجهة العام.

## Next Action

1. حمزة يشغّل الفحوصات ويتحقق يدوياً من محتوى ZIP.
2. حمزة يوافق على commit وpush.

## Do Not Do Yet

- لا TTS كامل.
- لا فيديو AI.
- لا ComfyUI.
- لا WanGP.
- لا production deploy.
- لا database/auth.
