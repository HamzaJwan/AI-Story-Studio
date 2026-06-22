# 00 — Start Here

**تاريخ الإنشاء:** 2026-06-22

هذا المجلد هو حزمة تشغيل أولية لـ **AI Story Studio**.  
الغرض منها أن تدخل المشروع في VS Code وتعطيه لـ Codex وGemini بدون فوضى.

## فلسفة المشروع المختصرة

AI Story Studio ليس مجرد Prompt box.  
هو منصة تحول القصة إلى:

1. سكريبت راوي.
2. مشاهد منظمة.
3. ملف `scenes.json` قابل للمراجعة.
4. Phase 1 لاحقاً: صوت MP3.
5. Phase 2 لاحقاً: صور سينمائية وMP4 مونتاج.
6. Phase 3 لاحقاً: فيديو AI قصير لبعض المشاهد.

## قرار المرحلة الحالية

**نبدأ بـ Phase 0 فقط.**

- Phase 0 فقط: واجهة + Backend + Ollama + Improve Story + Split Scenes + scenes.json.
- Phase 1/2/3 — DO NOT IMPLEMENT IN PHASE 0.
- Phase 1 لاحقاً: MVP صوت/MP3.
- لا تبدأ فيديو AI كامل.
- لا تبدأ Wan2.1/WanGP قبل نجاح الصوت والصور.

## ترتيب استخدام أدوات AI

### 1. Gemini / Antigravity — Reviewer
يعطي مراجعة للخطة والهيكل قبل التنفيذ.

استخدم:
`prompts/GEMINI_REVIEW_PROMPT.md`

### 2. Codex — Executor
ينفذ فقط بعد مراجعة Gemini وبعد موافقة المستخدم.

استخدم:
`prompts/CODEX_START_IMPLEMENTATION_PROMPT.md`

### 3. المستخدم / حمزة — Product Owner
يعطي:
- IP الخاص بـ Ollama.
- النموذج المطلوب.
- هل يبدأ Codex أم لا.
- هل يتم الانتقال إلى مرحلة تالية.

## Stop Conditions

أوقف التنفيذ وارجع للمستخدم إذا:
- لم يتم ضبط OLLAMA_BASE_URL.
- فشل الاتصال بـ Ollama.
- ظهر Mojibake في العربي.
- احتاجت المهمة API مدفوع.
- اقترح Codex إعادة هيكلة كبيرة.
- تم طلب تعديل `.env` أو طباعة أسرار.
