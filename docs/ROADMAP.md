# AI Story Studio — Roadmap

<!-- آخر تحديث: 2026-06-22 | المراجع: Antigravity -->

---

## 1. الحالة الحالية

| الحقل | القيمة |
|---|---|
| **Current Phase** | Phase 0.0 — Preflight & Foundation |
| **Current Status** | DONE LOCALLY — Pending Gemini review and Hamza approval to push |
| **Current Owner** | Hamza |
| **Current Executor** | Codex |
| **Current Reviewer** | Gemini / Antigravity |
| **Last Updated** | 2026-06-22 |
| **Current Decision** | لا تبدأ Phase 0.1 حتى يوافق حمزة على تقرير Preflight ويُضاف هذا الملف إلى الـ commit |

---

## 2. مبدأ المشروع

1. **Local-first** — يعمل محلياً على Windows قبل أي نشر.
2. **Docker-ready** — كل شيء قابل للتشغيل عبر `docker compose up`.
3. **GitHub source of truth** — لا تعديل بدون commit موثّق.
4. **AI-assisted, not AI-chaotic** — Codex منفذ، Gemini مراجع، حمزة يقرر.
5. **Arabic/RTL-first** — كل واجهة وكل ملف نصي يعامل العربي كأولوية.
6. **No paid API in Phase 0** — Ollama فقط عبر `.env`. لا OpenAI، لا Gemini API.
7. **Production-safe by design** — لا أسرار في Git، لا CORS مفتوح، لا hardcoded IPs.
8. **Small phases, no feature creep** — كل مرحلة لها نطاق ثابت وشرط انتقال واضح.

---

## 3. قواعد عدم التوسع

هذه القواعد غير قابلة للاستثناء إلا بموافقة صريحة من حمزة:

- ❌ لا TTS في Phase 0
- ❌ لا MP3 في Phase 0
- ❌ لا توليد صور في Phase 0
- ❌ لا فيديو AI في Phase 0
- ❌ لا ComfyUI / WanGP في Phase 0
- ❌ لا DB (SQLite أو غيرها) في Phase 0
- ❌ لا Auth / Login في Phase 0
- ❌ لا Redis / Celery / Queue في Phase 0
- ❌ لا Admin Settings page قبل Auth
- ❌ لا hardcoded IP أو URL في الكود
- ❌ لا أسرار أو API keys في Git
- ❌ لا تعديل `.env` من Codex
- ❌ لا `allow_origins=["*"]` في FastAPI
- ❌ لا push قبل مراجعة Gemini وموافقة حمزة

---

## 4. خارطة المراحل

| Phase | الاسم | الهدف | الحالة | المخرجات | شرط الانتقال |
|---|---|---|---|---|---|
| **0.0** | Preflight & Foundation | هيكل + Docker + UTF-8 + docs | ✅ DONE LOCALLY | Git ✓, Dockerfiles ✓, requirements.txt ✓, UTF-8 ✓ | موافقة حمزة + Gemini review |
| **0.1** | Ollama Story Workspace | Backend + Frontend + Ollama + Split Scenes | ⏳ NEXT | scenes.json, UI عربي جميل وحركي | Gemini review + check_utf8 pass + حمزة |
| **0.2** | Review & Stabilization | مراجعة + إصلاح + commit/push | ⏳ LATER | نظام مستقر وموثّق، git push | Gemini Approved + git push نظيف |
| **1.0** | MP3 Narrator Benchmark | اختبار SILMA TTS | ⬜ LATER | test_audio.wav قصير | نجاح Phase 0.2 |
| **1.1** | MP3 Narrator MVP | Pipeline صوت كامل | ⬜ LATER | MP3 قابل للتحميل | نجاح Phase 1.0 Benchmark |
| **2.0** | Cinematic Images + MP4 | SDXL/ComfyUI + FFmpeg | ⬜ LATER | 3 صور + MP4 أولي | نجاح Phase 1.1 |
| **3.0** | AI Video POC | WanGP/Wan2.1 مشهدين | ⬜ LATER | كليب 3-5 ثوانٍ | نجاح Phase 2.0 + VRAM كافٍ |
| **4.0** | Staging/Production | Portainer + Security | ⬜ LATER | نشر آمن ومستقر | نجاح Phase 3.0 أو قرار تجاري |

---

### Phase 0.0 — Preflight & Foundation
**الحالة:** ✅ DONE LOCALLY — Pending push

**ما أنجزه Codex:**
- Git initialized + remote linked (branch main ahead 1)
- Commit: `67d78a1 chore: prepare phase 0 foundation`
- Phase scope موحّد: لا TTS/Images/Video/ComfyUI/WanGP/Redis/Celery في Phase 0
- `backend/requirements.txt` أُنشئ (fastapi, uvicorn, pydantic, pydantic-settings, requests, python-dotenv)
- `backend/Dockerfile` يقرأ requirements.txt
- `frontend/Dockerfile` يتعامل مع غياب package.json بذكاء
- `docs/CODEX_IMPLEMENTATION_SOP.md` أُنشئ (كان مفقوداً)
- `check_utf8.py` نجح بعد `PYTHONIOENCODING=utf-8`
- 43 ملفاً في الـ commit

---

### Phase 0.1 — Ollama Story Workspace
**الحالة:** ⏳ NEXT — بعد موافقة حمزة

**الأهداف:**
- `backend/app/main.py` — FastAPI entry point
- `GET /health` و `GET /api/ai/ollama/health`
- Ollama adapter يقرأ `OLLAMA_BASE_URL` و `OLLAMA_MODEL` من `.env` فقط
- `POST /api/story/improve-narration` — تحسين القصة كسكريبت راوي
- `POST /api/story/split-scenes` — تقسيم القصة إلى مشاهد
- استخراج JSON صالح من رد Ollama + validation
- حفظ `data/projects/{project_id}/story.txt` و `scenes.json`
- Frontend: React + Vite + TypeScript + Tailwind + Framer Motion
- UI عربي RTL، شاشة واحدة، scene cards، download button

---

### Phase 0.2 — Review & Stabilization
**الحالة:** ⏳ LATER

**الأهداف:**
- Gemini يراجع كل تغييرات Phase 0.1
- إصلاح أي Mojibake أو مشاكل encoding
- `docker compose up --build` يعمل كاملاً
- `check_utf8.py` ينجح
- Git commit نظيف + push لـ GitHub
- تحديث `CURRENT_STAGE_SUMMARY.md` و `DECISION_LOG.md`

---

### Phase 1.0 — MP3 Narrator Benchmark
**الحالة:** ⬜ LATER

**الأهداف:**
- اختبار SILMA TTS على مقطع قصير (30-60 ثانية)
- مقارنة XTTS إذا احتجنا
- قياس الجودة والوقت والـ VRAM
- **لا نبني واجهة كبيرة قبل نجاح هذا الاختبار**

---

### Phase 1.1 — MP3 Narrator MVP
**الحالة:** ⬜ LATER

**الأهداف:**
- Pipeline: Story → Narration Script → Scenes → Voice Segments → Final MP3
- TTS adapter (SILMA أو البديل المختار في Phase 1.0)
- واجهة توليد صوت بسيطة + تحميل MP3

---

### Phase 2.0 — Cinematic Images + MP4
**الحالة:** ⬜ LATER

**الأهداف:**
- Visual prompts لكل مشهد
- اختبار SDXL / ComfyUI على 3 صور
- تركيب MP4: صور ثابتة + صوت + subtitles + Ken Burns transitions

---

### Phase 3.0 — AI Video POC
**الحالة:** ⬜ LATER

**الأهداف:**
- WanGP / Wan2.1 على مشهد واحد أو مشهدين فقط
- قياس: الجودة، الوقت، VRAM
- **ليس للاستخدام الإنتاجي في البداية**

---

### Phase 4.0 — Staging/Production
**الحالة:** ⬜ LATER

**الأهداف:**
- Portainer deployment
- فصل Development عن Production
- Security hardening (CORS، auth، rate limiting)
- Health checks + monitoring
- Backup strategy لـ data/projects
- لا exposure عام بدون auth

---

## 5. تعريف النجاح لكل مرحلة

### Phase 0.0
- ✅ **Done when:** Dockerfiles مكتملة، requirements.txt موجود، check_utf8.py ينجح، Gemini Approved، حمزة يوافق على push.
- ❌ **Failed if:** أي ملف لا يُقرأ بـ UTF-8، أو Docker build يفشل.
- 🛑 **Stop if:** Codex بدأ تنفيذ وظائف التطبيق قبل اكتمال Preflight.

### Phase 0.1
- ✅ **Done when:** `/api/ai/ollama/health` يرجع `ok: true`، `split-scenes` يرجع JSON صالح، UI يعرض المشاهد بدون Mojibake، download يعمل.
- ❌ **Failed if:** Mojibake في أي مخرج عربي، أو JSON من Ollama لا يُعالَج بعد 3 محاولات.
- 🛑 **Stop if:** Codex أضاف TTS / DB / Auth / فيديو، أو استخدم API مدفوع.

### Phase 0.2
- ✅ **Done when:** Gemini Approved، `git log` نظيف، `docker compose up` يعمل، `CURRENT_STAGE_SUMMARY.md` محدّث، push تم.
- ❌ **Failed if:** لا يزال هناك CORS مفتوح أو أسرار في الكود.
- 🛑 **Stop if:** اكتُشفت مشكلة معمارية كبيرة تحتاج إعادة تصميم.

### Phase 1.0
- ✅ **Done when:** SILMA تنتج صوتاً عربياً مفهوماً خلال 60 ثانية.
- ❌ **Failed if:** SILMA لا تعمل والجودة غير مقبولة بعد تجربة XTTS.
- 🛑 **Stop if:** لا يوجد TTS يعمل — ننتظر بديلاً قبل Phase 1.1.

### Phase 1.1
- ✅ **Done when:** MP3 كامل للقصة قابل للتحميل من الواجهة.
- ❌ **Failed if:** مقاطع الصوت غير متزامنة أو جودتها غير مقبولة.
- 🛑 **Stop if:** وقت التوليد يتجاوز 10 دقائق لقصة قصيرة.

### Phase 2.0
- ✅ **Done when:** 3 صور سينمائية + MP4 أولي يعمل.
- ❌ **Failed if:** SDXL/ComfyUI تستهلك VRAM أكثر مما هو متاح.
- 🛑 **Stop if:** الجودة المرئية أقل من مستوى النشر.

### Phase 3.0
- ✅ **Done when:** كليب 3-5 ثوانٍ قابل للمراجعة البشرية.
- ❌ **Failed if:** WanGP يفشل على VRAM المتاح.
- 🛑 **Stop if:** يستهلك أكثر من 24 ساعة لمشهد واحد.

### Phase 4.0
- ✅ **Done when:** التطبيق على Portainer بدون تدخل يدوي، environment variables مفصولة.
- ❌ **Failed if:** أسرار مكشوفة أو CORS مفتوح في production.
- 🛑 **Stop if:** لا يوجد backup strategy لـ data/projects.

---

## 6. Current Task Board

| الحالة | المهمة | المسؤول | ملاحظات |
|---|---|---|---|
| ✅ DONE LOCALLY | Phase 0.0 Preflight — Git + Dockerfiles + requirements + UTF-8 | Codex | commit: `67d78a1` |
| 🔍 IN REVIEW | Gemini يراجع Preflight ويُضيف ROADMAP.md | Gemini/Antigravity | الآن |
| ⏳ NEXT | حمزة يوافق على تقرير Preflight ويقرر push أو Phase 0.1 | Hamza | قرار إلزامي |
| ⏳ NEXT | Codex ينفذ Phase 0.1 — Backend + Frontend + Ollama | Codex | بعد موافقة حمزة فقط |
| ⏳ NEXT | Gemini يراجع Phase 0.1 | Gemini/Antigravity | بعد تقرير Codex |
| ⏳ NEXT | Git commit + push لـ Phase 0.1 | Hamza | بعد Gemini Approved |
| 🔵 LATER | SILMA TTS Benchmark — Phase 1.0 | Codex | بعد نجاح Phase 0.2 |
| 🔵 LATER | SDXL Image Benchmark — Phase 2.0 | Codex | بعد نجاح Phase 1.1 |
| 🔵 LATER | WanGP Video POC — Phase 3.0 | Codex | بعد نجاح Phase 2.0 |
| 🔵 LATER | Portainer Production Deploy | Hamza | بعد اكتمال MVP |

---

## 7. قرارات ثابتة حتى الآن

| القرار | السبب |
|---|---|
| React + Vite + TypeScript للواجهة | تصميم احترافي، ليس Gradio demo |
| FastAPI للـ backend | خفيف، Pydantic built-in، async-ready |
| Tailwind CSS + Framer Motion للـ UI | تصميم جميل وحركي عربي RTL |
| Ollama provider في Phase 0 | لا API مدفوع، محلي |
| `.env` للإعدادات (لا Admin page) | الأبسط والأأمن في Phase 0 |
| Adapter Pattern للـ AI providers | يسمح بإضافة OpenAI/Gemini لاحقاً بدون إعادة بناء |
| لا DB في Phase 0 | File-based storage كافٍ وأبسط |
| لا Auth في Phase 0 | local only، لا exposure عام |
| لا TTS/Video في Phase 0 | نثبت القيمة الأساسية أولاً |
| GitHub هو source of truth | لا تعديل بدون commit |
| Gemini reviewer + Codex executor | فصل واضح للأدوار |
| Production لاحقاً وليس الآن | نتجنب التعقيد المبكر |

---

## 8. قرارات مؤجلة

هذه النقاط لا تُناقَش ولا تُنفَّذ حتى يحين وقتها:

- ❓ **SILMA أم XTTS؟** → قرار Phase 1.0 Benchmark
- ❓ **SDXL فقط أم FLUX لاحقاً؟** → قرار Phase 2.0
- ❓ **ComfyUI أم WanGP؟** → قرار Phase 3.0
- ❓ **Admin page بعد Auth؟** → قرار Phase 4.0
- ❓ **DB بعد Phase 1؟** → يُقيَّم عند الحاجة لـ user sessions
- ❓ **Production private أم public؟** → قرار Hamza عند Phase 4.0
- ❓ **Users/Auth لاحقاً؟** → يُقيَّم بعد نجاح MVP كامل

---

## 9. بيانات Ollama المطلوبة من حمزة

> ⚠️ لا تضع أي IP حقيقي هنا. القيم تُوضع في `.env` فقط.

| المعلومة | القيمة | المكان |
|---|---|---|
| `OLLAMA_BASE_URL` | `[set in local .env only]` | `.env` فقط |
| `OLLAMA_MODEL` | `[set in local .env only]` | `.env` فقط |
| موقع Ollama | داخل نفس Windows/Docker Desktop أم سيرفر آخر؟ | حمزة يوضّح |
| نطاق URL | داخلي (LAN) فقط أم سيصل له staging لاحقاً؟ | حمزة يوضّح عند Phase 4.0 |

**قاعدة:** إذا لم يُعيَّن `OLLAMA_BASE_URL` في `.env`، يتوقف Codex ويطلب من حمزة.

---

## 10. Stop Conditions العامة

| الحالة | الإجراء |
|---|---|
| 🛑 Mojibake في أي مخرج عربي | أوقف، شغّل `check_utf8.py`، لا تكمل |
| 🛑 `check_utf8.py` يفشل | أصلح الترميز أولاً |
| 🛑 hardcoded IP أو URL في الكود | أزله، استبدل بـ env variable |
| 🛑 تعديل `.env` من Codex | ممنوع مطلقاً |
| 🛑 dependency كبيرة بدون موافقة | اكتب السبب، انتظر موافقة حمزة |
| 🛑 TTS أو Video قبل وقته | ممنوع في Phase 0 |
| 🛑 `allow_origins=["*"]` في FastAPI | استبدل بـ CORS_ORIGINS من `.env` |
| 🛑 Ollama غير متاح بعد محاولتين | أوقف، بلّغ حمزة |
| 🛑 JSON من Ollama غير صالح بعد 3 retries | أوقف، سجّل الخطأ |
| 🛑 Production change بدون موافقة | ممنوع مطلقاً |
| 🛑 API مدفوع (OpenAI/Gemini) | ممنوع في Phase 0 |
| 🛑 Codex يقترح refactor كبير | اكتب المقترح فقط، لا تنفذه |

---

## 11. كيف نستخدم هذا الملف

**قبل كل جلسة Codex أو Gemini:**
1. اقرأ هذا الملف لتعرف أين وصلنا.
2. راجع `CURRENT_STAGE_SUMMARY.md` لتفاصيل المهمة الحالية.
3. راجع `DECISION_LOG.md` للقرارات المتخذة.

**بعد كل مرحلة:**
- حدّث **Current Task Board** (Section 6) فقط.
- حدّث **الحالة الحالية** (Section 1).
- حدّث `CURRENT_STAGE_SUMMARY.md` و `DECISION_LOG.md`.

**إذا جاءت فكرة جديدة:**
- ضعها في القرارات المؤجلة (Section 8).
- لا تضفها إلى المرحلة الحالية.

**قاعدة الانتقال بين المراحل:**
> لا تنتقل للمرحلة التالية إلا بعد:
> 1. تحقق تعريف النجاح (Section 5).
> 2. موافقة حمزة الصريحة.
> 3. Git commit نظيف.
> 4. Gemini Approved.

> **ROADMAP هو مرجع الحالة. ليس ملف تصميم تفصيلي. لا يُعدَّل خلال التنفيذ إلا عند إتمام مرحلة أو تغيير قرار.**
