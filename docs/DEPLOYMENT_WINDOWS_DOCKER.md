# Deployment — Windows Docker Desktop

## Phase 0 local commands

```powershell
cd D:\Coding\ai-story-studio-win
Copy-Item .env.example .env
notepad .env
python scripts/check_utf8.py
docker compose config
docker compose up --build
```

## Expected URLs

```text
Frontend: http://localhost:5173
Backend:  http://localhost:8810
Health:   http://localhost:8810/health
```

## Troubleshooting

### Docker compose fails
- تحقق من Docker Desktop يعمل.
- تحقق من `.env` موجود.
- شغّل `docker compose config`.

### Arabic broken
- شغّل `python scripts/check_utf8.py`.
- تأكد VS Code encoding = UTF-8.

### Ollama unreachable
- تأكد السيرفر ping.
- افتح `OLLAMA_BASE_URL` من المتصفح أو curl.
- تحقق أن Ollama listens على network وليس localhost فقط.

## Production later

يُكتب لاحقاً بعد نجاح Phase 1.
