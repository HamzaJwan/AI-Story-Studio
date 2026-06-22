# دليل العمل مع الذكاء الاصطناعي — ADC Portal Platform

> **الهدف:** مرجع شامل لأي كودر AI جديد يبدأ العمل على هذا المشروع أو مشروع مشابه
> **المُعِد:** Antigravity (Google DeepMind) + Codex — بناءً على تدقيق أمني كامل (Stage 3.0)
> **آخر تحديث:** 2026-05-23
> **التصنيف:** داخلي — للمطورين والكودرز فقط

---

## ⚠️ تحذير حرج — مشكلة الترميز العربي (يجب قراءته أولاً)

هذا المشروع مرّ بمشكلة **Mojibake** (نص عربي يظهر كرموز مكسورة مثل `Ø§Ù„Ø±Ù‚Ù…`).

**السبب الجذري:** بعض الملفات المصدرية حُفظت بترميز **Windows-1252 (cp1252)** بدلاً من UTF-8.

### الأعراض التي تعرفك على المشكلة:

```typescript
// ❌ ملف مكسور — ما يظهر في الكود:
label: 'Ø§Ù„Ø±Ù‚Ù…'

// ❌ أو بعلامات استفهام:
label: 'الد?عة'   // الدفعة بالعربي الصحيح

// ✅ ملف صحيح:
label: 'الرقم الوطني'
```

### كيف تتحقق بسرعة:

```powershell
cmd /c python -c "
import sys; sys.stdout.reconfigure(encoding='utf-8')
with open('frontend/src/views/RequestsView.tsx', encoding='utf-8') as f:
    c = f.read()
bad = sum(1 for ch in c if 0x0080 <= ord(ch) <= 0x00FF)
print(f'Mojibake chars: {bad}')
# يجب أن يكون 0
"
```

### إذا وجدت المشكلة — الحل:

```powershell
# الملف الموجود في الـ repo جاهز للاستخدام:
cmd /c python fix_encoding.py
```

أو راجع الوثيقة الكاملة: **`docs/SESSION_WORK_LOG.md`** — القسم 2.

### قاعدة صارمة:

> لا تُعدّل أي ملف `.tsx` أو `.py` أو `.md` يحتوي على عربي  
> إلا **بعد** التحقق من أن ترميزه UTF-8 في VS Code (أسفل اليمين → "UTF-8")

---

## القسم الأول — فهم البيئتين (Local vs Production)


### البيئة المحلية (Docker Desktop)

```
المستخدم: للتطوير والاختبار فقط
الملف: docker-compose.internal-db.yml
متغيرات البيئة: .env.docker.local
الرابط: http://127.0.0.1:2028
```

**أوامر البداية والإيقاف:**

```powershell
# تشغيل كامل مع بناء الصور
docker compose --env-file .env.docker.local -f docker-compose.internal-db.yml up -d --build

# إيقاف بدون حذف البيانات
docker compose --env-file .env.docker.local -f docker-compose.internal-db.yml down

# إعادة بناء الـ frontend فقط (بعد تغييرات UI)
docker compose --env-file .env.docker.local -f docker-compose.internal-db.yml up -d --build frontend

# مشاهدة الـ logs
docker compose --env-file .env.docker.local -f docker-compose.internal-db.yml logs -f backend frontend
```

**الخدمات ووظيفتها:**

| الخدمة | النوع | الوظيفة |
|--------|-------|---------|
| `adc-setup` | one-shot | ينشئ مجلدات `/opt/Appdata/adc_portal/` |
| `adc-db` | persistent | MariaDB 10.11 — قاعدة البيانات |
| `adc-init` | one-shot | ينتظر DB ثم يشغّل migrations |
| `adc-backend` | persistent | FastAPI على port 2820 |
| `adc-frontend` | persistent | Nginx + React على port 2028 |
| `adc-redis` | persistent | Cache layer |
| `adc-backup` | persistent | نسخ احتياطية يومية |

> **مهم:** `adc-setup` و `adc-init` ينتهيان بـ `Exit 0` — هذا صحيح وليس خطأ.

**التحقق من الصحة محلياً:**

```powershell
# حالة الـ containers
docker compose --env-file .env.docker.local -f docker-compose.internal-db.yml ps

# التحقق الوظيفي
Invoke-WebRequest http://127.0.0.1:2028/api/v1/system/ready -UseBasicParsing
```

النتيجة المتوقعة:
```json
{"ready":true,"components":{"db":{"ready":true},"redis":{"ready":true},"queue":{"detail":"disabled"}}}
```

**بيانات الدخول المحلية (ENV=development):**
```
Username: TEST_ADMIN_USERNAME
Password: TEST_ADMIN_PASSWORD
```

---

### بيئة الإنتاج (Production)

```
الخادم: ADC_PRODUCTION_HOST
الإدارة: Portainer (http://PORTAINER_HOST:9000)
اسم الـ Stack: adc-portal-v2
الملف: docker-compose.production.yml
الرابط العام: https://adc.juanspace.org
```

**آلية النشر (CI/CD Pipeline):**

```
المطور يكتب كود
    ↓
git push origin main
    ↓
GitHub Actions يشتغل تلقائياً:
  1. backend-check  → Python compile
  2. frontend-build → npm build
  3. smoke-tests    → HTTP tests
  4. build-and-push → Docker images → GHCR
    ↓
Watchtower (على الخادم) يراقب كل 5 دقائق
    ↓
يكتشف صورة جديدة → يسحبها → يعيد تشغيل الـ container
    ↓
التحقق: GET /api/v1/system/version
```

**التحقق من نجاح النشر:**

```
1. docker logs adc-watchtower   (هل سحب صورة جديدة؟)
2. docker ps                    (كل الـ containers healthy؟)
3. GET /api/v1/system/version   (هل الـ gitCommit محدّث؟)
4. شريط الجانب في الـ UI        (هل يعرض رقم الإصدار الجديد؟)
```

**قاعدة ذهبية:** لا تتحقق بعينك — تحقق بالـ version endpoint.

---

## القسم الثاني — منهجية العمل الأمني

### ما تعلمناه من التدقيق الأمني (Stage 3.0)

هذا المشروع مرّ بتدقيق أمني كامل من نظامَي ذكاء اصطناعي مختلفَين:
- **Antigravity** (Google DeepMind)
- **Codex** (OpenAI)

النتائج كشفت أن معظم المشاكل لم تكن في الكود — بل في **ملفات التوثيق**.

---

### قواعد الأسرار (Secrets) — لا استثناء

```
✅ الصح:
- الأسرار في Portainer Environment Variables فقط
- ملفات .env محلية وغير مُتتبَّعة بـ Git
- استخدام ${VARIABLE_NAME} في docker-compose

❌ الخطأ الذي وقعنا فيه:
- نسخ قيم الأسرار داخل ملفات .md موثّقة
- إنشاء ملفات "integration report" تحتوي DATABASE_URL كاملة
- توثيق credentials في deploy/ plans
```

**قاعدة الكودر الجديد:**
> إذا كتبت قيمة سر حقيقية في أي ملف — حتى لو `# تعليق` أو `.md` — افترض أنه مكشوف.

---

### تسلسل الأولويات الأمنية (من التجربة الفعلية)

```
المستوى 1 — فوري (قبل أي شيء):
□ SECRET_KEY قوي وفريد في Portainer
□ لا أسرار في Git history
□ كلمة مرور admin ليست افتراضية

المستوى 2 — خلال أسبوع:
□ مكتبة JWT محدّثة وآمنة
□ Rate limiting في backend (ليس فقط Nginx)
□ Magic bytes validation للملفات المرفوعة

المستوى 3 — خلال شهر:
□ Refresh token revocation mechanism
□ Report endpoints permission checks
□ WebSocket auth بدون query string token
□ تنظيف Git history القديم
```

---

### ما هو صحيح في هذا المشروع (احتفظ به في أي مشروع جديد)

| الممارسة | السبب |
|----------|-------|
| Argon2 لتشفير كلمات المرور | أقوى من bcrypt |
| Account lockout بعد 10 محاولات | يمنع brute force |
| HSTS + CSP + security headers في Nginx | دفاع متعدد الطبقات |
| read_only containers + cap_drop ALL | يحدّ من الضرر عند الاختراق |
| Watchtower مع label-enable | لا يمس DB وRedis تلقائياً |
| Audit logging لكل العمليات الحساسة | يمكنك تتبع من فعل ماذا |
| RBAC server-side — ليس frontend فقط | لا يمكن تجاوزه من المتصفح |
| /docs و /openapi.json مغلقان في production | لا خارطة للـ API للمهاجمين |

---

## القسم الثالث — كيف تعمل مع كودر AI جديد

### قبل أن تعطي الكودر أي برومت

**أرسل له هذه الملفات أولاً (بالترتيب):**

```
1. docs/AGENT_RULES.md          ← القواعد غير القابلة للكسر
2. docs/ARCHITECTURE_FINAL.md   ← كيف يعمل النظام
3. docs/QUICK_REFERENCE.md      ← الأوامر السريعة
4. docs/AI_CODER_GUIDE.md       ← هذا الملف
```

---

### صيغة البرومت الصحيحة لمشروع جديد

```
أنت تعمل على [اسم المشروع].

السياق:
- Stack: [FastAPI / React / MariaDB / Redis / Docker]
- بيئة التطوير: Docker Desktop محلياً
- الإنتاج: Portainer على [IP]
- المستخدمون: [وصف المستخدمين]

قبل أي عمل، اقرأ:
- docs/AGENT_RULES.md
- docs/AI_CODER_GUIDE.md

قواعد صارمة:
1. لا تطبع أي قيمة سر أو password
2. لا تعدّل production مباشرة
3. لا تغيّر database schema بدون migration
4. اختبر محلياً أولاً دائماً
5. كل تغيير يحتاج موافقة

المهمة: [وصف واضح ومحدد]
النطاق: [ما يجب فعله + ما لا يجب لمسه]
```

---

### كيف تقرأ ردود الكودر AI

**علامات الكودر الجيد:**
- يقول "سأتحقق أولاً" قبل التعديل
- يوضح ما سيلمسه وما لن يلمسه
- يعطيك Stop Conditions واضحة
- يطلب تأكيداً قبل production actions

**علامات التحذير:**
- يبدأ بتعديل ملفات مباشرة بدون قراءة
- يقول "هذا آمن" بدون تحقق
- يطبع قيم database URL أو passwords
- يقترح refactor كبير لحل مشكلة صغيرة

---

### الفرق بين Antigravity و Codex (من التجربة)

| الجانب | Antigravity | Codex |
|--------|------------|-------|
| قراءة Git history | ✅ يبحث في .md files | ❌ يركّز على .env files |
| وصول SSH للإنتاج | ❌ لا | ✅ نعم (ميزة) |
| اكتشاف الأسرار في التوثيق | ✅ قوي | ⚠️ أغفل هذا |
| تغطية reports.py وws.py | ⚠️ ناقصة | ✅ شاملة |
| الأفضل لـ | Code review + Secrets audit | Production SSH checks |

**التوصية:** استخدم الاثنين معاً في التدقيق الأمني — كل واحد يكمل الآخر.

---

## القسم الرابع — بناء مشروع جديد من الصفر

### الهيكل الأساسي الموصى به

```
my-project/
├── backend/
│   ├── app/
│   │   ├── api/v1/         ← routes
│   │   ├── core/           ← config, security, rbac
│   │   ├── models/         ← SQLAlchemy models
│   │   ├── schemas/        ← Pydantic schemas
│   │   └── services/       ← business logic
│   ├── .env.example        ← قالب (بدون قيم حقيقية)
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── nginx.conf
│   └── Dockerfile
├── docs/
│   ├── AGENT_RULES.md      ← أول ملف تكتبه
│   ├── AI_CODER_GUIDE.md   ← انسخ هذا الملف
│   └── ARCHITECTURE.md
├── .env.example            ← بدون قيم حقيقية
├── .env.docker.local       ← في .gitignore
├── .gitignore              ← شامل من البداية
├── docker-compose.yml      ← للتطوير
└── docker-compose.production.yml ← للإنتاج
```

---

### `.gitignore` — ابدأ به من اليوم الأول

```gitignore
# Secrets — لا استثناء
.env
.env.local
.env.docker.local
.env.production
backend/.env
*.secret
*credentials*
*password*

# Deployment plans with credentials
deploy/
*.deployment.md

# Integration reports (قد تحتوي أسرار)
INTEGRATION_*.md
FINAL_INTEGRATION_*.md
*_STATUS.md

# Build artifacts
node_modules/
__pycache__/
dist/
*.pyc

# Local logs
*.log
backend_restart.log
```

---

### قائمة تحقق قبل أول Commit

```
□ .gitignore شامل ومكتمل
□ .env.example موجود (بقيم وهمية فقط)
□ لا توجد قيم أسرار حقيقية في أي ملف .md
□ AGENT_RULES.md موجود ومكتوب
□ docker-compose يستخدم ${VARIABLE_NAME} وليس قيماً مباشرة
□ SECRET_KEY مولّد عشوائياً: python -c "import secrets; print(secrets.token_hex(32))"
□ كلمة مرور admin ليست افتراضية
□ Swagger/OpenAPI مغلق في production (DOCS_URL="")
```

---

### قائمة تحقق الأمان قبل الإطلاق

```
□ HTTPS مفعّل (Cloudflare Tunnel أو Let's Encrypt)
□ Security headers في Nginx (HSTS, CSP, X-Frame-Options)
□ Rate limiting على login endpoint
□ Account lockout مُفعّل
□ Argon2 أو bcrypt لتشفير كلمات المرور
□ JWT مع expiry معقول (60 دقيقة access, 7 أيام refresh)
□ CORS محدود لـ origins معروفة فقط
□ read_only: true للـ containers
□ Portainer محمي (ليس مكشوفاً للإنترنت)
□ Watchtower مع --label-enable
□ Backup strategy موثّقة
□ Audit logging لكل العمليات الحساسة
```

---

## القسم الخامس — توصيات ذكية من التجربة

### 1. الأسرار — قاعدة اللاعودة

إذا وصل سر إلى Git history — حتى في commit قديم — افترض أنه مكشوف للأبد.
الحل الوحيد هو:
1. دوران فوري للسر في Portainer
2. تنظيف Git history بـ `git filter-repo` أو `BFG`
3. إبلاغ كل من يملك نسخة من الـ repo

### 2. التوثيق — لا تضع أسراراً فيه أبداً

```
# خاطئ:
SECRET_KEY="abc123real"  ← في ملف .md

# صح:
SECRET_KEY=[REDACTED]  ← أو وصف فقط بدون قيمة
```

### 3. مراحل العمل الأمني (Stage Model)

**لا تخلط المشاكل في مرحلة واحدة.** المنهجية الصحيحة:

```
Stage 3.1  → حل تسريب الأسرار (أولوية قصوى)
Stage 3.1b → تنظيف Git history
Stage 3.2  → تحديث مكتبات JWT، رفع الملفات
Stage 3.3  → تحسين الجلسات (refresh token revocation)
Stage 3.4  → Deployment immutability (بدل :latest)
```

كل مرحلة = برومت منفصل = scope محدد = لا خلط.

### 4. التحقق الثنائي (Dual AI Review)

للمشاريع الحساسة، اطلب تدقيقاً من **نظامَي AI مختلفَين**.
كل نظام له نقاط قوة مختلفة:
- أحدهما قد يجد ما يغفله الآخر
- التدقيق الثنائي أشمل من أي تدقيق منفرد

### 5. Production SSH — اعرف من يملكه

```
قاعدة: فقط شخص واحد يملك SSH للإنتاج
قاعدة: AI Coder لا يحتاج SSH مباشرة
قاعدة: كل عملية production = موافقة يدوية من المسؤول
```

### 6. الـ Watchtower — نعمة ونقمة

**نعمة:** تحديث تلقائي بدون تدخل
**نقمة:** إذا دفعت كوداً معطوباً → ينشر نفسه تلقائياً

**الحل:** GitHub Actions smoke tests قبل كل push

```yaml
# في ci.yml — هذا يحمي الإنتاج
jobs:
  smoke-tests:
    needs: [backend-check, frontend-build]
    # ... يختبر before البناء
  build-and-push:
    needs: [smoke-tests]  # ← لا ينشر إلا بعد نجاح الاختبارات
```

### 7. الـ :latest Tag — خطر مخفي

```
المشكلة: :latest يتغيّر → لا يمكنك rollback بسهولة
الحل المستقبلي: استخدم image digest أو version tag
ghcr.io/user/repo/backend:v1.2.3  ← أفضل
ghcr.io/user/repo/backend:latest  ← خطر في production
```

### 8. قبل أي مشروع جديد — اسأل هذه الأسئلة

```
□ من يملك SSH للخادم؟
□ أين تُخزَّن الأسرار؟ (Portainer / Vault / GitHub Secrets)
□ هل هناك CI/CD؟ أم نشر يدوي؟
□ من يملك الـ Git repo؟ هل هو private؟
□ ما هي سياسة النسخ الاحتياطي؟
□ من المسؤول عن تحديثات الأمان؟
□ هل هناك بيانات حساسة (شخصية / عسكرية / طبية)؟
```

---

## ملخص سريع — للكودر الجديد

```
قبل أي عمل:       اقرأ AGENT_RULES.md
للتطوير:          docker-compose.internal-db.yml + .env.docker.local
للإنتاج:          Portainer → stack adc-portal-v2
للتحقق:           /api/v1/system/version + docker ps
للأسرار:          Portainer فقط — لا Git — لا .md files
لأي تغيير أمني:   Stage منفصل + موافقة صريحة
للتدقيق الأمني:   استخدم Antigravity + Codex معاً
```

---

*وثيقة حية — يجب تحديثها بعد كل stage أمني أو تغيير معماري رئيسي.*
*المُعِد: Antigravity AI + Codex AI — بناءً على تجربة فعلية مع ADC Portal.*

---
## ملحق مراجعة تقنية سريعة (2026-05-23)

### قواعد إلزامية للكودرز الآليين (مستخرجة من الكود)
- في المصادقة: لا تفترض انتهاء الجلسة مباشرة عند 401؛ يوجد refresh تلقائي مرة واحدة (`frontend/src/api/client.ts:61-70`, `79-97`).
- مسارات WebSocket يجب أن تعتمد `AUTH_INIT` بعد الاتصال، وليس تمرير توكن في URL كمسار أساسي (`backend/app/api/v1/ws.py:42-53`, `frontend/src/context/NotificationContext.tsx:39-53`).
- أي endpoint حساس يجب أن يمر عبر `require_permission`/`require_any_permission` (`backend/app/api/deps.py:113-137`).
- في رفع الطلاب الجماعي: الاستجابة قد تحتوي أخطاء صفوف مع نجاح جزئي لنفس العملية (`backend/app/api/v1/students.py:1026-1028`, `1148-1160`).
- توليد رقم مرجع التقرير يتم من الخادم عبر `/reports/generate-reference` ولا يجب توليده client-side (`backend/app/api/v1/reports.py:61-103`, `frontend/src/views/ReportsView.tsx:320-326`).
