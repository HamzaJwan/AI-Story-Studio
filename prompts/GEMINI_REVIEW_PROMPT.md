# Gemini / Antigravity Review Prompt

أنت الآن مراجع معماري وتقني لمشروع AI Story Studio.

## اقرأ أولاً
- docs/00_START_HERE.md
- docs/AI_AGENT_RULES.md
- docs/CODER_TOOL_SOP.md
- docs/ARCHITECTURE.md
- docs/UI_UX_MOTION_BRIEF.md
- docs/API_CONTRACTS.md
- docs/CURRENT_STAGE_SUMMARY.md
- docs/DECISION_LOG.md
- .env.example
- docker-compose.yml

## المطلوب منك
راجع المشروع قبل تنفيذ Codex.

لا تكتب كود.
لا تعدل ملفات.
لا تقترح بناء ضخم.
لا تقترح فيديو AI في Phase 0.

## ركز على
1. هل المرحلة محددة وصغيرة؟
2. هل Codex سيعرف ماذا يفعل؟
3. هل OLLAMA_BASE_URL قابل للضبط؟
4. هل هناك خطر أسرار؟
5. هل هناك خطر Mojibake/UTF-8؟
6. هل التصميم المقترح واضح وجميل؟
7. هل API contracts كافية لـ Phase 0؟
8. هل هناك overengineering؟
9. هل يوجد شيء ناقص قبل التنفيذ؟

## أجب بهذا الشكل فقط

```text
Decision: Approved / Approved with changes / Blocked

Critical blockers:
- ...

Required changes before Codex:
- ...

Recommended improvements:
- ...

Files Codex may touch in Phase 0:
- ...

Files Codex must not touch:
- ...

Final instruction to Codex:
...
```
