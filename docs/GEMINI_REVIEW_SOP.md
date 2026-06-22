# SOP — Gemini / Antigravity Review

## دور Gemini
المراجعة لا التنفيذ.

## المطلوب من Gemini

1. قراءة docs الأساسية.
2. التأكد أن المشروع لا يبدأ كبيراً.
3. التأكد أن Ollama قابل للضبط من `.env`.
4. مراجعة مخاطر الترميز العربي.
5. مراجعة عدم وجود أسرار.
6. مراجعة UX: هل الشاشة تخدم الكاتب أم تغرقه؟
7. مراجعة أن Codex لا يبدأ فيديو AI مبكراً.
8. إعطاء قرار:
   - Approved
   - Approved with changes
   - Blocked

## لا تطلب من Gemini
- كتابة كود واسع.
- تغيير الهيكل.
- استخدام APIs مدفوعة.
- وضع IP أو passwords داخل الملفات.

## قالب مراجعة Gemini

```text
Decision: Approved / Approved with changes / Blocked

Critical issues:
Major risks:
Minor improvements:
Suggested changes before Codex:
Files that Codex may touch:
Files that Codex must not touch:
Final recommendation:
```
