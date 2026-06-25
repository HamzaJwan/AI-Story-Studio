# AI Story Studio — Roadmap

<!-- آخر تحديث: 2026-06-24 | المراجع: Hamza -->

---

## 1. الحالة الحالية

| الحقل | القيمة |
|---|---|
| **Current Phase** | Phase 2.0 — Image Benchmark Lab |
| **Current Status** | ✅ PASS — صورة حقيقية تولّدت فعلياً (ComfyUI + SDXL base، 768×768، ~14.7s، PNG حقيقي تحقَّق بصرياً) |
| **Current Owner** | Hamza |
| **Current Executor** | Claude |
| **Current Reviewer** | Hamza |
| **Last Updated** | 2026-06-25 |
| **Current Decision** | الشبكة تعافت بعد التجمّد الذي أثّر على SILMA وSDXL — كانت تذبذباً مؤقتاً، لا عطلاً دائماً. Phase 2.0 PASS تقنياً، لكن **يحتاج موافقة حمزة على جودة الصورة فعلياً** قبل أي دمج في المنتج (شرط التوقف #9). لا UI صور ولا Phase 2.1 قبل تلك الموافقة |

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
| **0.0** | Preflight & Foundation | هيكل + Docker + UTF-8 + docs | ✅ DONE | Git ✓, Dockerfiles ✓, requirements.txt ✓, UTF-8 ✓ | موافقة حمزة |
| **0.1** | Ollama Story Workspace | Backend + Frontend + Ollama + Split Scenes | ✅ DONE | scenes.json, UI عربي RTL | check_utf8 pass + حمزة |
| **0.2** | Project Workspace | حفظ/تحميل/تعديل مشاريع محلية (JSON) | ✅ DONE | Project CRUD endpoints, scene editing | تحقق يدوي + حمزة |
| **0.3** | Scene Editing UX Polish | تحسين واجهة تعديل المشاهد (frontend-only) | ✅ DONE | scene cards, validation, stats bar | تحقق يدوي + حمزة |
| **0.4** | Story Package Export | تصدير حزمة المشروع كـ ZIP | ✅ DONE | export.zip endpoint + زر تحميل | تحقق حمزة + git push |
| **0.5** | Hardware-Aware Benchmark Foundation | توثيق العتاد + Benchmark Gate رسمي | ✅ DONE | HARDWARE_PROFILE.md, BENCHMARK_PROTOCOL.md | تحقق حمزة + git push |
| **1.0** | TTS Benchmark | اختبار SILMA TTS كـ isolated lab | ✅ DONE (isolated lab) | WAV/MP3 ناجح على AI Server GPU | نجاح Phase 0.5 |
| **1.1** | Audio Bridge MVP | جسر اتصال backend/frontend لـ TTS Worker خارجي (بدون engine حقيقي) | ✅ DONE | `/api/tts/*` endpoints + لوحة "استوديو الصوت" | commit `668af46`، push تم — **توليد صوت فعلي يبقى ممنوعاً حتى Benchmark Gate = PASS** |
| **1.2** | TTS Worker Lab API | worker حقيقي منفصل (Piper، SILMA معطّل مؤقتاً) في `deploy/ai-server/tts-worker/` | ✅ PASS (Piper) | FastAPI worker شغّال + WAV حقيقي على AI Server | تحقق حمزة + git push |
| **1.3** | Connect App to TTS Worker | ربط Audio panel بمشهد واحد فعلياً | ✅ PASS | job حقيقي + audio player حقيقي يعملان | تحقق حمزة + git push |
| **1.4** | Project Audio Export | صوت لكل المشاهد + إضافته لـ export.zip | ✅ PASS | `audio/*.wav` + `final_story.wav` داخل ZIP | تحقق حمزة + git push |
| **2.0** | Image Benchmark Lab | SDXL/ComfyUI على AI Server | ✅ PASS (تقنياً) | PNG حقيقي 768×768 تحقَّق بصرياً | **يحتاج موافقة حمزة على الجودة** قبل Phase 2.1 |
| **3.0** | AI Video POC | WanGP/Wan2.1 مشهدين | ⬜ LATER — **يحتاج Benchmark Gate = PASS** | كليب 3-5 ثوانٍ | Benchmark Gate PASS لـ Video + نجاح Phase 2.0 |
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
**الحالة:** ✅ DONE

**الأهداف:**
- `backend/app/main.py` — FastAPI entry point
- `GET /health` و `GET /api/ai/ollama/health`
- Ollama adapter يقرأ `OLLAMA_BASE_URL` و `OLLAMA_MODEL` من `.env` فقط
- `POST /api/story/improve-narration` — تحسين القصة كسكريبت راوي
- `POST /api/story/split-scenes` — تقسيم القصة إلى مشاهد
- استخراج JSON صالح من رد Ollama + validation
- حفظ `data/projects/{project_id}/story.txt` و `scenes.json`
- Frontend: React + Vite + TypeScript + CSS عادي (بدون Tailwind/Framer Motion)
- UI عربي RTL، شاشة واحدة، scene cards، download button

---

### Phase 0.2 — Project Workspace
**الحالة:** ✅ DONE

**الأهداف:**
- Project CRUD محلي (JSON files تحت `data/projects/`)
- إنشاء/حفظ/تحميل/تعديل مشروع
- تصدير `scenes.json` للنسخة المحفوظة

---

### Phase 0.3 — Scene Editing UX Polish
**الحالة:** ✅ DONE

**الأهداف:**
- Scene cards قابلة للطي والنشر + أزرار تحريك/نسخ/إضافة/حذف
- Validation warnings + scene stats bar
- Frontend-only، لا تغيير في backend

---

### Phase 0.4 — Story Package Export
**الحالة:** ✅ IMPLEMENTED LOCALLY — Pending Hamza verification and push

**الأهداف:**
- `GET /api/projects/{project_id}/export.zip` يرجع ZIP يحتوي story.txt + improved_story.txt + scenes.json + metadata.json
- زر تحميل واحد في الواجهة، فعّال فقط بعد حفظ المشروع
- لا dependencies جديدة (Python standard library فقط)

---

### Phase 0.5 — Hardware-Aware Benchmark Foundation
**الحالة:** ✅ DONE

**الأهداف:**
- `docs/HARDWARE_PROFILE.md` — توثيق العتاد الحقيقي (Local Dev Machine + AI Server) بدون أسرار.
- `docs/BENCHMARK_PROTOCOL.md` — قاعدة رسمية: لا TTS/Image/Video engine يدخل المنتج إلا بعد Benchmark Gate (PASS/CANDIDATE/BLOCKED/REJECTED) مسجَّل بحقول واضحة (زمن، VRAM، جودة، ناتج فعلي).
- توثيق فقط — لا تنفيذ TTS/Image/Video في هذه المرحلة.
- Phase 2.0 (Images) وPhase 3.0 (Video) لا تبدأ إلا بعد Benchmark Gate = PASS لكل منها.

---

### Phase 1.0 — TTS Benchmark
**الحالة:** ✅ DONE (isolated lab benchmark)

**الأهداف:**
- اختبار SILMA TTS على مقطع قصير — ناجح على AI Server GPU (WAV + MP3، ~256.95s لأول توليد)
- يبقى isolated lab تحت `deploy/ai-server/silma-lab/` — لا دمج داخل التطبيق
- AllTalk scaffold مضاف كـ candidate إضافي، بدون integration

---

### Phase 1.1 — Audio Bridge MVP
**الحالة:** ✅ DONE

**الأهداف:**
- Backend connector (`TtsWorkerClient`) يتصل بخدمة `tts-worker` خارجية مستقبلية عبر `TTS_SERVICE_URL` فقط — لا دمج مباشر للموديلات، لا SILMA/AllTalk فعلي.
- `TTS_ENABLED` معطّل افتراضياً (`false`) — أي بيئة بدون env إضافية تستمر بالعمل بدون أي تغيير ظاهر.
- 3 endpoints: `GET /api/tts/health` (يرجع 200 دائماً)، `POST /api/projects/{id}/tts/jobs` و`GET /api/tts/jobs/{id}` (يرجعان 503 إذا غير مفعّل).
- لوحة "استوديو الصوت" (badge تجريبي) في الواجهة — تعرض الحالة بوضوح، أزرار التوليد معطّلة إذا الخدمة غير مفعّلة، بدون أي صوت وهمي.

---

### Phase 1.2 — TTS Worker Lab API
**الحالة:** ✅ PASS (Piper) — SILMA `BLOCKED` على نفس الـ worker بسبب الشبكة

**ما تم:**
- `deploy/ai-server/tts-worker/` — FastAPI worker كامل (`/health`, `POST /api/tts/jobs`, `GET /api/tts/jobs/{id}`, `GET /api/tts/jobs/{id}/files`, `GET .../download/{format}`)، يدعم محركين عبر `ENGINE` env var.
- بُني وشُغِّل فعلياً على AI Server (`ssh ai-story-server`، repo في `~/ai-story-studio-fresh`)، GPU مؤكَّد داخل الـ container (`nvidia-smi`: RTX 4060 Ti 8188 MiB).
- **SILMA (`ENGINE=silma`):** الكود يعيد استخدام دوال `tools/tts/silma_benchmark.py` المُثبَتة سابقاً، لكن تحميل الموديل (~2GB) من HuggingFace Xet CDN **تجمّد فعلياً مرتين** (نفس عدد البايتات بالضبط عبر نوافذ 15-30 ثانية متعددة، retransmissions مؤكَّدة) — مشكلة شبكة حقيقية على AI Server الليلة، ليست خطأ كود. الكود يبقى موجوداً للمحاولة لاحقاً.
- **Piper (`ENGINE=piper`, الافتراضي الآن):** صوت `ar_JO-kareem-medium` (HF repo `rhasspy/piper-voices`، مرخّص MIT، ليس صوت حمزة ولا مشهور). تم توليد **2 ملف WAV حقيقي**: نص قصير (cold run ~6 دقائق مع تحميل الصوت تحت شبكة متقطعة، 221,740 bytes، 5.03s) ونص أطول مع علامات ترقيم وأرقام (warm run **~3.8 ثانية فقط**، 756,268 bytes، 17.15s). كلا الملفين تم تحميلهما عبر `/download/wav` والتحقق من المحتوى الصوتي الفعلي (max amplitude 32767، RMS~4051، 98.6% non-zero samples — ليس صمتاً أو تالفاً).
- تفاصيل كاملة في `docs/TTS_ENGINE_BENCHMARK_MATRIX.md` → "Phase 1.2 Worker Attempt — 2026-06-24".

---

### Phase 1.3 — Connect App to TTS Worker
**الحالة:** ✅ PASS

**ما تم:**
- `backend/app/routers/tts.py` يرسل نص المشهد الفعلي (`narration_ar`) أو نص المشروع كاملاً كحقل `text` للـ worker — كان غائباً في Phase 1.1/1.2.
- `GET /api/tts/jobs/{id}/download/{format}` endpoint جديد على backend الرئيسي يُمرّر الصوت من الـ worker — المتصفح لا يتصل بـ `TTS_SERVICE_URL` مباشرة أبداً.
- Audio panel: حالة Job بالعربي، `<audio>` حقيقي + زر تحميل يظهران فقط بعد `status: "done"` فعلي.
- **تحقق فعلي:** مشهدان حقيقيان من مشروع محفوظ ولّدا صوتاً حقيقياً (435,756 bytes / 404,012 bytes) عبر السلسلة الكاملة (frontend route → backend → AI Server worker → Piper → تحميل عبر backend). أعيد التحقق بعد إعادة بناء صورة الـ worker من Dockerfile المُصحَّح (لا فقط container مُرقَّع يدوياً).
- لا كسر لأي endpoint قديم (فحص كامل: scenes.json, export.zip, projects CRUD, health, config, ollama health).

---

### Phase 1.4 — Project Audio Export
**الحالة:** ✅ PASS

**ما تم:**
- `POST /api/projects/{id}/tts/generate-all` يولّد صوتاً حقيقياً لكل مشاهد المشروع (job منفصل لكل مشهد، sequential، لا يتوقف عند فشل مشهد واحد).
- audio metadata (`audio_generated_at`, `audio_bytes`, `audio_format`) محفوظة داخل project JSON فعلياً.
- `export.zip` يحتوي الآن `audio/scene_XX.wav` لكل مشهد له صوت + `audio/final_story.wav` (دمج WAV خام بدون ffmpeg، لا MP3 — موثَّق كـ limitation صريح في `metadata.json`)، بدون كسر بنية ZIP للمشاريع بلا صوت.
- **تحقق فعلي:** مشروع حقيقي بـ 6 مشاهد → توليد صوت لكل المشاهد بنجاح (0 فشل) → export.zip يحتوي 6 ملفات WAV + final_story.wav (2,050,092 bytes، 46.49 ثانية، صالح فعلياً).
- اكتُشف وأُصلح bug حقيقي أثناء الاختبار (`scenes_export()` كان يفشل عند وجود `datetime` في بيانات الصوت) قبل اعتبار المرحلة منجزة.

---

### Phase 2.0 — Image Benchmark Lab
**الحالة:** ✅ PASS تقنياً — **يحتاج موافقة حمزة على الجودة قبل أي دمج**

**ما تم:**
- `deploy/ai-server/comfyui-lab/` — Dockerfile (ComfyUI + `--lowvram`)، docker-compose.yml، workflow JSON (نص-إلى-صورة، 768×768).
- **اختيار المحرك:** ComfyUI 0.26.0 + SDXL base 1.0 fp16 (~6.5GB فعلياً على القرص) — بحث ويب أولاً (ComfyUI أخف من A1111، SDXL يعمل على 8GB بصعوبة، FLUX يحتاج VRAM أكبر)، ثم تحقق فعلي.
- **محاولة أولى فشلت:** تحميل الـ checkpoint تجمّد بسبب شبكة AI Server المتقطعة (نفس نمط SILMA السابق) — وُثِّق كـ BLOCKED، تم حذف الملف الجزئي.
- **محاولة ثانية نجحت** بعد تأكد الشبكة تعافت (فحص سرعة حقيقي: ~2.67MB/s)، التحميل اكتمل (6.5GB فعلياً).
- **نتيجة Benchmark Gate الفعلية:**
  - الأمر: `POST /prompt` بملف `workflow_sdxl_txt2img.json` (نفس المرفق في الـ repo).
  - الناتج: `benchmark_phase2_00001_.png` — 768×768 RGB، 693,857 bytes.
  - الزمن: **~14.7 ثانية** (cold run، يشمل تحميل الموديل من القرص لأول مرة).
  - VRAM: قمة 6995 MiB (812 MiB متبقية فقط — ضيق جداً لكن بدون OOM)، يعود لـ 4959 MiB بعد التحميل.
  - **تحقق بصري فعلي:** الصورة عُرضت ونُظر إليها مباشرة — مشهد متماسك حقيقي (شخص يجلس عند نافذة ليلاً بضوء دافئ)، يطابق النص المُدخَل تماماً، بدون تلف أو فراغ.
- **الفرق الجوهري بين هذا الـ PASS وقرار دمج فعلي:** هذا PASS تقني (الأنابيب تعمل، الصورة حقيقية وسليمة). **لم يُقيَّم بعد من حمزة كجودة منتج مقبولة** — شرط التوقف #9 ("تحتاج تقييم جودة بشري لصوت/صورة/فيديو") لا يزال قائماً قبل Phase 2.1.

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

### Phase 0.5
- ✅ **Done when:** `HARDWARE_PROFILE.md` و`BENCHMARK_PROTOCOL.md` موجودان وموثّقان بلا أسرار، حمزة يوافق على push.
- ❌ **Failed if:** أي password/token/IP غير موجود مسبقاً في docs تسرّب إلى الملفات.
- 🛑 **Stop if:** أي محاولة لدمج TTS/Image/Video فعلياً خلال هذه المرحلة.

### Phase 1.0
- ✅ **Done when:** SILMA تنتج صوتاً عربياً مفهوماً خلال 60 ثانية.
- ❌ **Failed if:** SILMA لا تعمل والجودة غير مقبولة بعد تجربة XTTS.
- 🛑 **Stop if:** لا يوجد TTS يعمل — ننتظر بديلاً قبل Phase 1.1.

### Phase 1.1 — Audio Bridge MVP
- ✅ **Done when:** `/api/tts/health` يرجع `configured: false` بدون env إضافية، endpoints الـ job ترجع 503 بوضوح، لوحة "استوديو الصوت" تظهر بدون كسر الواجهة، Phase 0.4/0.x لم تنكسر.
- ❌ **Failed if:** التطبيق يتعطل بدون `TTS_SERVICE_URL`، أو الواجهة تعرض نجاحاً وهمياً (صوت أو job مزيّف).
- 🛑 **Stop if:** أي محاولة لتشغيل SILMA/AllTalk أو GPU فعلياً ضمن هذه المرحلة.

> توليد صوت فعلي كامل (MP3/WAV حقيقي من `tts-worker` مبني فعلياً) يبقى خطوة لاحقة منفصلة، ولا تبدأ إلا بعد Benchmark Gate = PASS حسب `docs/BENCHMARK_PROTOCOL.md`.

### Phase 1.2 — TTS Worker Lab API
- ✅ **Done when:** الـ worker مبني فعلياً على AI Server، `nvidia-smi` يظهر داخل الـ container، job حقيقي ينتج `audio.wav` قابل للتشغيل والتحميل عبر `GET .../download/wav`. **تحقَّق بتاريخ 2026-06-24 عبر Piper.**
- ❌ **Failed if:** الـ container لا يرى GPU، أو لا يوجد WAV حقيقي بعد التشغيل، أو استُخدمت reference voice غير مسموحة.
- 🛑 **Stop if:** لا يوجد وصول SSH/Docker فعلي على AI Server — **تم حل هذا عبر SSH key alias `ai-story-server`.**

### Phase 2.0
- ✅ **Done when:** Benchmark Gate يسجّل `PASS` لمحرك الصور على AI Server، ثم 3 صور سينمائية + MP4 أولي يعمل.
- ❌ **Failed if:** Benchmark Gate لم يصدر PASS، أو SDXL/ComfyUI تستهلك VRAM أكثر مما هو متاح فعلياً.
- 🛑 **Stop if:** الجودة المرئية أقل من مستوى النشر، أو لم يصدر Benchmark Gate PASS بعد.

### Phase 3.0
- ✅ **Done when:** Benchmark Gate يسجّل `PASS` لمحرك الفيديو على AI Server، ثم كليب 3-5 ثوانٍ قابل للمراجعة البشرية.
- ❌ **Failed if:** Benchmark Gate لم يصدر PASS، أو WanGP يفشل على VRAM المتاح فعلياً.
- 🛑 **Stop if:** يستهلك أكثر من 24 ساعة لمشهد واحد، أو لم يصدر Benchmark Gate PASS بعد.

### Phase 4.0
- ✅ **Done when:** التطبيق على Portainer بدون تدخل يدوي، environment variables مفصولة.
- ❌ **Failed if:** أسرار مكشوفة أو CORS مفتوح في production.
- 🛑 **Stop if:** لا يوجد backup strategy لـ data/projects.

---

## 6. Current Task Board

| الحالة | المهمة | المسؤول | ملاحظات |
|---|---|---|---|
| ✅ DONE | Phase 0.0 Preflight — Git + Dockerfiles + requirements + UTF-8 | Claude | commit: `67d78a1` |
| ✅ DONE | Phase 0.1 — Backend + Frontend + Ollama | Claude | scenes.json يعمل |
| ✅ DONE | Phase 0.2 — Project Workspace (Project CRUD) | Claude | git push تم |
| ✅ DONE | Phase 0.3 — Scene Editing UX Polish | Claude | commit: `360ed62` |
| ✅ DONE | Phase 0.4 — Story Package Export (export.zip) | Claude | commit: `528a0f6`, push تم |
| ✅ DONE | Phase 0.5 — Hardware-Aware Benchmark Foundation | Claude | commit: `eee692f`, push تم |
| ✅ DONE (isolated lab) | SILMA TTS Benchmark — Phase 1.0 | Claude | WAV/MP3 ناجح على AI Server GPU |
| ✅ DONE | Phase 1.1 — Audio Bridge MVP (`/api/tts/*` + لوحة الصوت) | Claude | commit: `668af46`, push تم |
| ✅ PASS (Piper) | Phase 1.2 — TTS Worker Lab API (`deploy/ai-server/tts-worker/`) | Claude | WAV حقيقي على AI Server؛ SILMA BLOCKED بسبب الشبكة، الكود محفوظ |
| ✅ PASS | Phase 1.3 — Connect App to TTS Worker | Claude | صوت حقيقي لمشهدين عبر الواجهة الكاملة |
| ✅ PASS | Phase 1.4 — Project Audio Export | Claude | export.zip بصوت حقيقي لمشروع 6 مشاهد كامل |
| ✅ PASS (تقني) | Image Benchmark Lab — Phase 2.0 | Claude | PNG حقيقي 768×768، **يحتاج موافقة جودة حمزة** قبل Phase 2.1 |
| 🔵 LATER | WanGP Video POC — Phase 3.0 | — | يحتاج Benchmark Gate = PASS + AI Server access |
| 🔵 LATER | Portainer Production Deploy | Hamza | بعد اكتمال MVP |

---

## 7. قرارات ثابتة حتى الآن

| القرار | السبب |
|---|---|
| React + Vite + TypeScript للواجهة | تصميم احترافي، ليس Gradio demo |
| FastAPI للـ backend | خفيف، Pydantic built-in، async-ready |
| CSS عادي (`styles.css`) بدون مكتبات UI خارجية | يبقي الفرونت خفيفاً بدون dependencies إضافية |
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
| 🛑 لا يوجد SSH key/session لـ AI Server (password وحده لا يكفي — الـ harness يمنع تمريره داخل أوامر) | أوقف تنفيذ أي مرحلة تحتاج AI Server، اكتب الكود/التوثيق الممكن محلياً فقط، وأبلغ حمزة بالحاجز بدل افتراض نجاح |

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
