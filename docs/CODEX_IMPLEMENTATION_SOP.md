# SOP — Codex Implementation

## Codex يبدأ بهذا

1. اقرأ:
   - `docs/00_START_HERE.md`
   - `docs/AI_AGENT_RULES.md`
   - `docs/ARCHITECTURE.md`
   - `docs/API_CONTRACTS.md`
   - `docs/CURRENT_STAGE_SUMMARY.md`

2. اعرض خطة قصيرة:
   - الملفات التي ستنشئها.
   - الملفات التي ستعدلها.
   - كيف ستتحقق.
   - ما الذي لن تلمسه.

3. انتظر موافقة المستخدم.

## Phase 0 Implementation Scope

المسموح:
- إنشاء backend FastAPI skeleton.
- إنشاء frontend React/Vite skeleton.
- إنشاء endpoint health.
- إنشاء Ollama adapter.
- إنشاء endpoint split-scenes.
- إنشاء UI واحدة جميلة.
- إنشاء file-based project storage.

غير مسموح:
- TTS كامل إذا لم ينجح benchmark.
- Video generation.
- DB migrations.
- Auth/users.
- Production deployment.
- Secrets.

## التحقق المطلوب

```powershell
python scripts/check_utf8.py
docker compose config
# بعد تنفيذ backend/frontend:
docker compose up --build
# ثم:
Invoke-WebRequest http://localhost:8810/health -UseBasicParsing
```

## Expected Deliverable من Codex

- واجهة مبدئية جميلة.
- API health.
- API لتقسيم القصة عبر Ollama.
- إعدادات env.
- README محدث.
- CURRENT_STAGE_SUMMARY محدث.
