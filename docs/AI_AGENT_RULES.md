# AI Agent Rules — Codex / Gemini / Antigravity

## قواعد غير قابلة للكسر

1. اقرأ `docs/00_START_HERE.md` أولاً.
2. افحص `git status` قبل أي تعديل.
3. لا تعدل `.env`.
4. لا تطبع مفاتيح أو أسرار أو tokens.
5. لا تستخدم OpenAI API أو Gemini API أو أي API مدفوع إلا إذا طلب المستخدم صراحة.
6. لا تبدأ فيديو AI في Phase 0/1.
7. لا تغير بنية المشروع الكبيرة بدون موافقة.
8. لا تضف dependency إلا بسبب واضح ومكتوب.
9. لا تكتم أخطاء API.
10. لا تعرض بيانات وهمية كأنها حقيقية.
11. كل ملف عربي يجب حفظه UTF-8.
12. أي تغيير يجب توثيقه في `docs/CURRENT_STAGE_SUMMARY.md`.
13. إذا ظهرت مشكلة encoding/Mojibake، توقف فوراً وشغّل `scripts/check_utf8.py`.

## دور Codex

Codex منفذ:
- يقرأ الوثائق.
- يقترح plan قصير.
- ينتظر موافقة.
- ينفذ بملفات قليلة.
- يشغل تحقق.
- يكتب ملخص.

## دور Gemini / Antigravity

Gemini مراجع:
- يراجع الهيكل.
- يبحث عن المخاطر.
- يمنع overengineering.
- يراجع الأمن والأسرار.
- يراجع UX والمنطق.
- لا ينفذ تعديلات مباشرة إلا بإذن.

## صيغة تقرير أي AI بعد العمل

```text
Summary:
Files changed:
Validation:
Risks:
Next step:
Need user decision:
```
