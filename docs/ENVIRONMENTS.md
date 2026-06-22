# Environments

## Local Windows Development

المسار المقترح:

```text
D:\Coding\ai-story-studio-win
```

الأدوات:
- VS Code
- Docker Desktop
- Git
- Node.js LTS
- Python 3.11+
- Ollama على سيرفر داخلي

## Local .env

`.env.example` قالب فقط.  
انسخه إلى `.env` محلياً:

```powershell
Copy-Item .env.example .env
```

ثم عدّل:
- OLLAMA_BASE_URL
- OLLAMA_MODEL

## Production / Portainer

ليس ضمن Phase 0.  
لا تنشر Portainer قبل نجاح:
- backend health
- frontend build
- Ollama split scenes
- Gemini review

## Secrets Rule

الأسرار لا تدخل:
- `.md`
- `.env.example`
- frontend
- Git history
