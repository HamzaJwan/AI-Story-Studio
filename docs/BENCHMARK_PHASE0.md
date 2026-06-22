# Phase 0 Benchmark Plan

## الهدف

قبل بناء التطبيق الكامل، نثبت أن الأساس يعمل:

1. واجهة Phase 0.
2. Backend Phase 0.
3. اتصال Ollama.
4. تحسين القصة كسكريبت راوي.
5. تقسيم قصة عربية إلى مشاهد.
6. حفظ `scenes.json`.
7. سلامة UTF-8.
8. واجهة تعرض النتائج.

Phase 0 فقط: واجهة + Backend + Ollama + Improve Story + Split Scenes + scenes.json.

## مخرجات Phase 0

```text
data/projects/{project_id}/story.txt
data/projects/{project_id}/scenes.json
```

## اختبارات النجاح

| الاختبار | النجاح |
|---|---|
| UTF-8 | `python scripts/check_utf8.py` ينجح |
| Ollama Health | يرجع ok |
| Split Scenes | يرجع JSON صالح |
| UI | تعرض المشاهد بدون تكسير عربي |
| Git | لا توجد أسرار في الملفات |

## لا يدخل في Phase 0

- SILMA TTS integration.
- MP3 export.
- ComfyUI.
- WanGP.
- User auth.
- Production deployment.

## قرار الانتقال إلى Phase 1

ننتقل إلى Phase 1 إذا:
- story split يعمل.
- output واضح.
- Gemini review approved.
- Codex لم يكسر الهيكل.
