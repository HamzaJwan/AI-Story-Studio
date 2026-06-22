# PROJECT PLAYBOOK — AI Story Studio

## الهدف

بناء تطبيق محلي/قابل للنشر يساعد المستخدم على تحويل القصة العربية إلى:
- سكريبت صوتي.
- مشاهد منظمة.
- صوت روائي.
- ملفات قابلة للتصدير.
- لاحقاً صور ومونتاج وفيديو.

## المبادئ

1. Local-first.
2. Docker-ready.
3. GitHub-controlled.
4. AI-assisted, not AI-chaotic.
5. RTL Arabic first.
6. لا أسرار في Git.
7. لا ربط مباشر بمزود AI واحد.
8. كل توليد AI يجب أن يكون قابلاً للمراجعة والحفظ أو الرفض.

## مراحل المشروع

### Phase 0 — Benchmark / Foundation
- هيكل المشروع.
- وثائق SOP.
- ضبط Ollama IP.
- اختبار `/health`.
- توليد `scenes.json` من قصة عربية.
- لا TTS إلزامي داخل التطبيق بعد.

### Phase 1 — MP3 Narrator MVP
- إدخال القصة.
- تحسينها كسكريبت راوي.
- تقسيمها إلى مشاهد.
- توليد ملفات narration text.
- توليد audio عبر TTS adapter إن توفر.
- تحميل MP3.

### Phase 2 — Cinematic Images + MP4
- توليد visual prompts.
- تصدير prompt لكل مشهد.
- دعم ComfyUI/SDXL لاحقاً.
- تركيب MP4 بصور ثابتة + صوت + subtitles.

### Phase 3 — AI Video Clips
- تجربة WanGP/Wan2.1 لمشهدين فقط.
- ليس للاستخدام الإنتاجي في البداية.

## تعريف النجاح في أول أسبوع

- يعمل المشروع محلياً على Windows.
- يقرأ القصة العربية بدون مشاكل ترميز.
- يتصل بـ Ollama.
- يخرج `scenes.json` منظم.
- الواجهة جميلة وواضحة.
- يمكن مراجعة مخرجات AI قبل اعتمادها.
