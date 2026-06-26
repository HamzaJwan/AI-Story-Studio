# AI Story Studio — Windows Workspace

تطبيق محلي (FastAPI + React/Vite) يحوّل قصة عربية إلى مشروع كامل: مشاهد قابلة للتعديل، صوت، صور، فيديو مركّب، وترجمة — عبر Ollama على الشبكة المحلية وworker اختياريين للصوت والصور على AI Server.

**الحالة الحالية: AI Story Studio — Production Studio RC2** — الخط الكامل (قصة → مشاهد → صوت → صور → استمرارية → فيديو → ترجمة → تصدير ZIP) منفّذ ومُتحقَّق منه بمعطيات حقيقية، وأُضيف عليه أساس Studio إنتاجي: تتبع تقدّم بالـjobs بدل الانتظار الصامت، خط زمني للمشاهد، مكتبة أصول، لوحة مراجعة جودة، فيديو بحركة Ken Burns خفيفة اختيارية، استوديو صور مستقل، ولوحة حالة محركات AI. التفاصيل والقيود في [`docs/CURRENT_STAGE_SUMMARY.md`](docs/CURRENT_STAGE_SUMMARY.md)، [`docs/FEATURE_INVENTORY.md`](docs/FEATURE_INVENTORY.md)، و[`docs/PRODUCTION_STUDIO_RC2_REPORT.md`](docs/PRODUCTION_STUDIO_RC2_REPORT.md).

## ما الذي يفعله التطبيق فعلاً

1. كتابة/تحسين قصة عربية عبر Ollama — القصص الطويلة (أكثر من ~6000 حرف) تُحسَّن على أجزاء بدل فشلها.
2. تقسيمها إلى مشاهد قابلة للتعديل (عنوان، نص راوٍ، وصف بصري، مدة).
3. توليد صوت لكل مشهد ولكامل القصة عبر TTS worker خارجي (اختياري)، مع تتبع تقدّم حقيقي عبر job.
4. توليد صورة لكل مشهد عبر ComfyUI/SDXL على AI Server (اختياري، جودة `CANDIDATE` لا نهائية)، أو صورة مستقلة من وصف واحد عبر "استوديو الصور المستقل".
5. ضبط استمرارية بصرية (شخصيات/مكان/أسلوب) تُحقن تلقائياً في كل برومبت صورة، مع معاينة الـ prompt المُجمَّع قبل التوليد.
6. تجميع فيديو MP4 واحد من الصور + الصوت عبر ffmpeg — وضع ثابت أو حركة Ken Burns خفيفة، مع/بدون تلاشي بين المشاهد (بدون حركة AI حقيقية).
7. تصدير ترجمة `.srt`/`.vtt` متزامنة مع توقيت الفيديو الفعلي.
8. خط زمني لحالة كل مشهد، مكتبة أصول لكل ملفات المشروع، ولوحة مراجعة جودة (اعتماد/إعادة/رفض) قبل التصدير النهائي.
9. تحميل حزمة المشروع كاملة (`export.zip`).

**ما لا يفعله بعد:** لا فيديو بالذكاء الاصطناعي (motion حقيقي)، لا قاعدة بيانات/مستخدمين متعددين، لا مساعد محادثة محلي مدمج (Open WebUI يبقى منفصلاً). هذه مخططة لاحقاً في [`docs/ROADMAP.md`](docs/ROADMAP.md).

## التشغيل السريع (Quick Start)

```powershell
cd D:\Coding\ai-story-studio-win
Copy-Item .env.example .env
# عدّل .env محلياً: على الأقل OLLAMA_BASE_URL لخادم Ollama على شبكتك المحلية
docker compose up -d --build
```

افتح المتصفح على `http://localhost:5173` (أو المنفذ في `FRONTEND_PORT`).

- Backend: `http://localhost:8810`
- Health check: `http://localhost:8810/health`

### أول شيء تفعله في الواجهة

1. اكتب قصة في خطوة "القصة" (أو اضغط "تحميل مثال" لنص جاهز).
2. اضغط "تحسين القصة" ثم "تقسيم إلى مشاهد" — يُحفظ المشروع تلقائياً.
3. تابع الخطوات بالترتيب من شريط "Studio Workflow" أعلى الصفحة: المشاهد ← الصوت ← الصور ← الفيديو والترجمة ← الخط الزمني ← مكتبة الأصول ← مراجعة الجودة ← استوديو الصور المستقل ← التصدير.

### شروط الصوت والصور (اختيارية)

الصوت والصور يحتاجان worker خارجي يعمل على AI Server (LAN)، وليس جزءاً من `docker compose up` الافتراضي:

- الصوت: `TTS_ENABLED=true` و `TTS_SERVICE_URL=http://<AI_SERVER_IP>:8851` بعد تشغيل `deploy/ai-server/tts-worker/`.
- الصور: `IMAGE_SERVICE_ENABLED=true` و `IMAGE_SERVICE_URL=http://<AI_SERVER_IP>:8188` بعد تشغيل `deploy/ai-server/comfyui-lab/`.

إن لم تُفعَّل، تظهر في الواجهة رسالة واضحة بأن الخدمة غير مفعّلة — لا تعطّل بقية التطبيق. المتصفح لا يتصل بهذه الخدمات مباشرة أبداً؛ كل الاتصال يمر عبر backend فقط.

### أين تُحفظ الملفات

- بيانات كل مشروع: `data/projects/{project_id}/` (JSON + `audio/` + `images/` + `video/`)، كل هذا **مستثنى من Git** (`.gitignore`).
- حالة الـjobs (تتبع تقدّم تحسين القصة/توليد الصوت/الصور/الفيديو): `data/jobs/*.json`، محلية فقط ومستثناة من Git أيضاً — ليست قاعدة بيانات، فقط ملفات JSON صغيرة لكل عملية طويلة.
- `export.zip` (زر "تحميل ZIP" في أي خطوة) يجمع كل ما تم توليده حتى الآن: `story.txt`, `improved_story.txt`, `scenes.json`, `metadata.json`, `subtitles/story.srt`, `subtitles/story.vtt`, `audio/*.wav`, `images/*.png`, `video/final_story.mp4` — يُولَّد عند الطلب من البيانات المحفوظة، وليس ملفاً ثابتاً.

## قبل تشغيل Codex / مراجعة المشروع

اقرأ بالترتيب:

1. `docs/00_START_HERE.md`
2. `docs/AI_AGENT_RULES.md`
3. `docs/ARCHITECTURE.md`
4. `docs/API_CONTRACTS.md`
5. `docs/CURRENT_STAGE_SUMMARY.md`
6. `docs/MANUAL_QA_CHECKLIST.md` — خطوات التجربة اليدوية الكاملة

## ضبط Ollama

انسخ `.env.example` إلى `.env` ثم عدّل:

```env
OLLAMA_BASE_URL=http://YOUR_OLLAMA_IP:11434
OLLAMA_MODEL=qwen2.5:7b
```

لا تضع أسرار أو IP حقيقي داخل Git — `.env` مستثنى من التتبع، استخدم `.env.example` كقالب فقط.
