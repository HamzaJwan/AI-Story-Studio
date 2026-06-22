# AI Story Studio Project Playbook

هذا الملف هو دليل تشغيل مستقل لمشروع **AI Story Studio**. الهدف منه أن تعطيه لأي أداة برمجة ذكية مثل Codex أو Gemini أو Antigravity لكي تفهم طريقة العمل الصحيحة من البداية، بدون الحاجة إلى تمرير كل وثائق مشروع سابق.

الفكرة الأساسية:

> لا نريد تطبيقاً يكدس شاشات وخيارات عشوائية.  
> نريد منصة تساعد الكاتب على اتخاذ قرارات إبداعية، بناء عالم قصصي، تنظيم الشخصيات، توليد مسودات، ومراجعة جودة السرد بطريقة قابلة للتوسع.

---

## 1. فلسفة المشروع

AI Story Studio ليس مجرد واجهة لإرسال Prompt إلى نموذج ذكاء اصطناعي.

المنصة يجب أن تكون:

- مساحة عمل للقصص والمشاريع.
- نظاماً لتنظيم الشخصيات، العوالم، الفصول، المشاهد، الحبكات، والأحداث.
- طبقة ذكاء تساعد الكاتب، لا تستبدله.
- قابلة لإضافة مزودين مختلفين للذكاء الاصطناعي لاحقاً.
- قابلة للنشر محلياً وعلى سيرفر عام بدون خلط البيئات.

المبدأ المنتج:

> النموذج يعطي نصاً.  
> AI Story Studio يعطي سياقاً، قرارات، مراجعات، وبنية قصة.

---

## 2. طريقة العمل العامة

نشتغل بثلاث طبقات واضحة:

1. **Local Development**
   - التطوير اليومي على الجهاز المحلي.
   - تشغيل الخدمات عبر Docker Desktop أو أوامر التطوير المباشرة.
   - الاختبارات والتجارب تتم هنا أولاً.

2. **Public/Staging Environment**
   - نشر تجريبي أو عام على سيرفر.
   - الإدارة عبر Portainer أو Docker Compose.
   - لا نرفع أي تغيير قبل أن يثبت محلياً.

3. **GitHub Source of Truth**
   - GitHub هو المصدر الرسمي للكود.
   - كل تغيير مهم يتم عبر branch أو commit واضح.
   - لا نعتمد على تعديلات مباشرة في السيرفر كحقيقة نهائية.

---

## 3. هيكل المشروع المقترح

البنية المقترحة:

```text
ai-story-studio/
  backend/
    app/
      routers/
      services/
      models/
      db/
      ai_providers/
      story_engine/
    tests/
    Dockerfile
  frontend/
    src/
      views/
      components/
      services/
      stores/
      styles/
    Dockerfile
  docs/
    PROJECT_PLAYBOOK.md
    ARCHITECTURE.md
    AI_AGENT_RULES.md
    ENVIRONMENTS.md
    DEPLOYMENT.md
    API_CONTRACTS.md
    DECISION_LOG.md
    CURRENT_STAGE_SUMMARY.md
    CHANGELOG.md
  docker-compose.yml
  docker-compose.prod.yml
  .env.example
  .gitignore
  README.md
```

لا يجب أن يبدأ المشروع كبيراً. المهم أن يبدأ منظماً.

---

## 4. المكونات الأساسية

### Frontend

مسؤول عن تجربة الكاتب:

- لوحة المشاريع.
- محرر القصة.
- ملفات الشخصيات.
- بناء العالم.
- المخطط الزمني.
- المشاهد والفصول.
- نتائج ومقترحات الذكاء الاصطناعي.
- مراجعات الجودة.

قواعد الواجهة:

- لا تعرض كل شيء دفعة واحدة.
- اعرض القرار أو الخطوة التالية أولاً.
- التفاصيل تكون قابلة للفتح عند الحاجة.
- اجعل المسار واضحاً: ماذا أكتب؟ ماذا أراجع؟ ما المشكلة؟ ما الاقتراح؟

### Backend

مسؤول عن:

- API.
- إدارة المشاريع والقصص.
- قواعد البيانات.
- طبقة الاتصال بمزودي الذكاء الاصطناعي.
- حفظ السياق والذاكرة.
- معالجة المهام الطويلة.
- الصلاحيات.
- التصدير والاستيراد.

### AI Provider Adapter

لا تربط المنصة مباشرة بمزود واحد.

استخدم طبقة وسيطة:

```text
AIProvider
  generate_text()
  revise_text()
  summarize()
  extract_characters()
  score_scene()
```

بهذا يمكن لاحقاً تبديل أو إضافة:

- OpenAI
- Gemini
- Anthropic
- Local models
- أي مزود آخر

بدون إعادة بناء التطبيق.

### Story Engine

طبقة منطق المنتج:

- تحليل المشهد.
- متابعة تناسق الشخصية.
- اكتشاف ثغرات الحبكة.
- اقتراح أحداث.
- تلخيص الفصول.
- بناء continuity map.
- توليد بطاقات قرارات للكاتب.

هذه الطبقة أهم من مجرد API للنموذج.

---

## 5. العمل المحلي عبر Docker Desktop

الهدف من Docker Desktop محلياً:

- تشغيل backend/frontend/database بنفس طريقة قريبة من السيرفر.
- تقليل مشاكل “يعمل عندي فقط”.
- تسهيل إضافة خدمات مثل Redis أو PostgreSQL أو MinIO.

الخطوات العامة:

```bash
git clone <repo-url>
cd ai-story-studio
cp .env.example .env
docker compose up --build
```

قواعد مهمة:

- لا تضع أسرار حقيقية في `.env.example`.
- `.env` لا يدخل Git.
- أي خدمة جديدة تضاف إلى `docker-compose.yml` يجب توثيق سببها.
- إذا احتجت بيانات تجريبية، اجعلها seed واضحة وغير حساسة.

أمثلة خدمات محلية محتملة:

- Backend API.
- Frontend dev server.
- PostgreSQL.
- Redis للمهام.
- MinIO لتخزين الملفات والصور.
- Worker للمهام الطويلة.

---

## 6. البيئة العامة عبر Portainer

Portainer يستخدم لإدارة النشر العام أو staging.

طريقة العمل الصحيحة:

1. نبني image أو نستخدم compose stack.
2. نرفع التحديث إلى GitHub.
3. نسحب التحديث في السيرفر أو نعيد نشر Stack.
4. نتحقق من health checks.
5. نراقب logs.
6. إذا فشل التحديث، نرجع للإصدار السابق.

قواعد Portainer:

- لا تعدل الكود يدوياً داخل container.
- لا تجعل container هو مصدر الحقيقة.
- لا تخزن الأسرار في ملفات داخل repo.
- استخدم Environment Variables في Portainer أو secret manager.
- استخدم volumes فقط للبيانات التي يجب أن تبقى.

مثال خدمات public:

```text
reverse-proxy
frontend
backend
postgres
redis
worker
storage
```

الأمان:

- افتح فقط المنافذ المطلوبة.
- اجعل قاعدة البيانات داخل network داخلي.
- لا تعرض DB مباشرة على الإنترنت.
- استخدم HTTPS.
- فعل backup للبيانات قبل التحديثات الكبيرة.

---

## 7. GitHub Workflow

GitHub هو المصدر الرسمي.

الفروع المقترحة:

```text
main        إصدار مستقر
develop     تطوير متكامل إذا احتجناه
feature/*   ميزة محددة
fix/*       إصلاح محدد
docs/*      وثائق فقط
```

قاعدة العمل:

- كل تغيير له هدف واضح.
- لا تخلط refactor كبير مع feature جديدة.
- لا تعدل ملفات كثيرة بدون سبب.
- commit message يشرح السبب وليس فقط “update”.
- قبل merge، شغل الاختبارات أو تحقق يدوي موثق.

أمثلة commit جيدة:

```text
feat: add story workspace skeleton
fix: preserve project context when generating scene draft
docs: document AI provider adapter contract
```

---

## 8. قواعد العمل مع أدوات الذكاء الاصطناعي

أي AI coding tool يجب أن يقرأ هذه الملفات أولاً:

1. `docs/PROJECT_PLAYBOOK.md`
2. `docs/CURRENT_STAGE_SUMMARY.md`
3. `docs/ARCHITECTURE.md`
4. `docs/API_CONTRACTS.md`
5. `docs/DECISION_LOG.md`

ثم يقرأ الملفات المتعلقة بالمهمة فقط.

قواعد صارمة للـ AI:

- لا تعدل `.env`.
- لا تطبع مفاتيح API أو tokens.
- لا تمسح ملفات أو تعيد هيكلة المشروع بدون طلب واضح.
- لا تضف dependency إلا إذا لها سبب قوي.
- لا تكتم أخطاء API في الواجهة.
- لا تعرض أرقام أو نتائج وهمية على أنها حقيقية.
- لا تغير العقود API contracts بدون تحديث الوثائق.
- لا تخلط frontend وbackend وdeployment في تغيير واحد إلا إذا المهمة تتطلب ذلك.
- لا يترك dev server أو process غامض بدون توضيح.

قاعدة ذهبية:

> اقرأ، افهم، غيّر أقل قدر كافٍ، تحقق، وثق.

---

## 9. كيف نمنع التخريب أثناء البرمجة

قبل أي تعديل:

- افحص `git status`.
- اعرف الملفات التي ستتغير.
- اقرأ النمط الموجود في الكود.
- حدد نطاق التغيير.

أثناء التعديل:

- عدّل ملفات قليلة.
- لا تغيّر أسماء عامة إلا لسبب.
- لا تكسر routes أو API قديمة بدون migration.
- لا تضع بيانات تجريبية داخل production code.

بعد التعديل:

- شغل build أو tests المتاحة.
- افتح الصفحة أو endpoint.
- تحقق من console/logs.
- وثق ما تغير.

إذا ظهر خطأ:

- أصلح السبب، لا تخفيه.
- لا تجعل الواجهة تعرض صفر بدلاً من فشل API.
- اكتب رسالة واضحة للمستخدم: “تعذر جلب البيانات”.

---

## 10. قابلية التوسع

لكي يبقى AI Story Studio قابلاً للتوسع:

### استخدم Contracts

كل endpoint مهم يجب أن له عقد واضح:

```json
{
  "data": {},
  "meta": {
    "source": "",
    "confidence": "",
    "limitations": []
  },
  "errors": []
}
```

### استخدم Registry Patterns

بدلاً من hardcoding:

- Model registry.
- Prompt template registry.
- Export format registry.
- Story analysis rule registry.
- AI provider registry.

### افصل المنطق عن الواجهة

الواجهة تعرض.

الخدمات تحسب.

الـ story engine يقرر.

مزود الذكاء الاصطناعي يولد.

### لا تربط المنتج بموديل واحد

لا تجعل الكود يقول:

```text
openaiOnlyGenerateStory()
```

الأفضل:

```text
storyGenerationService.generate(provider, request)
```

---

## 11. التحديثات والنشر

أي تحديث يمر بهذه السلسلة:

1. تطوير محلي.
2. اختبار محلي.
3. commit.
4. push.
5. build.
6. deploy على staging/public.
7. health check.
8. مراقبة logs.
9. توثيق النتيجة.

لا نرفع للعام لمجرد أن الكود اشتغل مرة واحدة.

Rollback:

- احتفظ بإصدار image سابق.
- لا تغير schema قاعدة البيانات بدون migration قابلة للتراجع أو خطة واضحة.
- قبل تغييرات البيانات، خذ backup.

---

## 12. الوثائق المطلوبة من اليوم الأول

لا نحتاج وثائق كثيرة، لكن نحتاج وثائق صحيحة:

### `PROJECT_PLAYBOOK.md`

هذا الدليل.

### `ARCHITECTURE.md`

يرسم مكونات النظام والعلاقات بينها.

### `AI_AGENT_RULES.md`

قواعد التعامل مع Codex/Gemini/Antigravity.

### `ENVIRONMENTS.md`

شرح local/staging/production والمتغيرات المطلوبة بدون أسرار.

### `DEPLOYMENT.md`

خطوات Docker Desktop وPortainer.

### `API_CONTRACTS.md`

كل endpoint وعقده.

### `DECISION_LOG.md`

كل قرار معماري مهم ولماذا اتخذناه.

### `CURRENT_STAGE_SUMMARY.md`

أين وصلنا الآن وما التالي.

### `CHANGELOG.md`

تاريخ التغييرات.

---

## 13. خطة بناء AI Story Studio

### Phase 0 — التأسيس

- إنشاء repo.
- تجهيز Docker.
- تجهيز frontend/backend skeleton.
- تجهيز docs الأساسية.
- اختيار قاعدة البيانات.
- إعداد `.env.example`.

### Phase 1 — مساحة المشروع القصصي

- إنشاء مشروع قصة.
- حفظ العنوان والوصف والنوع.
- إدارة الشخصيات الأساسية.
- إدارة الفصول والمشاهد.
- محرر نص بسيط.

### Phase 2 — طبقة الذكاء

- AI provider adapter.
- prompt templates.
- توليد مشهد.
- تلخيص مشهد.
- اقتراح تحسين.
- حفظ history للنتائج.

### Phase 3 — Story Intelligence

- تحليل تناسق الشخصيات.
- اكتشاف ثغرات الحبكة.
- timeline.
- worldbuilding consistency.
- action cards للكاتب.

### Phase 4 — الملفات والتصدير

- تصدير Markdown/PDF/DOCX.
- إدارة صور ومراجع.
- نسخ احتياطي للمشروع.

### Phase 5 — التعاون والنشر العام

- حسابات وصلاحيات.
- مشاركة مشروع.
- comments.
- نشر preview.

---

## 14. شكل شاشة الإدارة في المشروع الجديد

حتى في مشروع قصصي، لا نريد “ERP viewer” أو “Prompt viewer”.

الشاشة الرئيسية يجب أن تعرض:

- المشاريع النشطة.
- آخر مشاهد تحتاج مراجعة.
- تناقضات الشخصيات.
- أحداث بدون ربط زمني.
- مشاهد ضعيفة الإيقاع.
- مقترحات متابعة.
- تنبيهات واضحة.

التفاصيل تكون collapsed أو داخل صفحات فرعية.

---

## 15. مثال Prompt تعطيه لأداة AI

استخدم هذا كنص بداية لأي أداة برمجة:

```text
أنت تعمل على مشروع AI Story Studio.

اقرأ أولاً:
- docs/PROJECT_PLAYBOOK.md
- docs/CURRENT_STAGE_SUMMARY.md
- docs/ARCHITECTURE.md
- docs/API_CONTRACTS.md
- docs/DECISION_LOG.md

قواعد العمل:
- لا تعدل .env ولا تطبع أسرار.
- لا تنفذ تغييرات واسعة بدون سبب.
- لا تضف بيانات وهمية كأنها حقيقية.
- لا تكتم أخطاء API في الواجهة.
- عدّل أقل عدد ممكن من الملفات.
- حافظ على قابلية التوسع: provider adapters, contracts, registries.
- بعد التعديل شغّل التحقق المناسب وحدث CURRENT_STAGE_SUMMARY.md إذا تغيرت المرحلة.

المهمة الحالية:
[اكتب المهمة هنا بوضوح]

المخرجات المطلوبة:
- الملفات المعدلة
- ما تم تغييره
- كيف تم التحقق
- القيود المتبقية
```

---

## 16. تعريف النجاح

المشروع يسير صح إذا:

- يمكن تشغيله محلياً بسهولة.
- يمكن نشره عبر Portainer بدون تعديلات يدوية داخل السيرفر.
- GitHub يحتوي الحقيقة الكاملة للكود.
- الوثائق تكفي لأي AI tool يبدأ من غير فوضى.
- كل إضافة جديدة تدخل كنمط قابل للتوسع، لا كترقيعة.
- الواجهة تساعد المستخدم على القرار، لا تغرقه في التفاصيل.

---

## 17. ملاحظات أمان نهائية

- الأسرار تبقى خارج Git.
- لا توجد مفاتيح API داخل frontend.
- أي endpoint يستدعي AI يجب أن يكون من backend.
- سجلات النظام لا تطبع prompts حساسة أو مفاتيح.
- المستخدم يعرف متى النص مولد بالذكاء ومتى هو محفوظ منه.
- كل توليد مهم يجب أن يكون قابل للمراجعة والحفظ أو الرفض.

---

## 18. الخلاصة

AI Story Studio يجب أن يبدأ صغيراً، لكن بعقلية صحيحة:

- Local-first.
- Docker-ready.
- GitHub-controlled.
- Portainer-deployable.
- AI-assisted but not AI-chaotic.
- Decision-first for the writer.
- Extensible by design.

هذا الملف هو نقطة البداية. بعد إنشاء المشروع الجديد، انسخه إلى:

```text
docs/PROJECT_PLAYBOOK.md
```

ثم أنشئ الملفات المساندة المذكورة في قسم الوثائق، وابدأ التنفيذ مرحلة مرحلة.
