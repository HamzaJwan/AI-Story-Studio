# AI Story Studio — Windows Workspace

مشروع أولي منظم للعمل عبر VS Code + Codex كمُنفّذ، وAntigravity/Gemini كمراجع.

## الهدف الأول
لا نبدأ بفيديو AI كامل. نبدأ بالمسار الواقعي:

1. إدخال قصة عربية.
2. تحسينها كسكريبت راوي.
3. تقسيمها إلى مشاهد.
4. توليد `scenes.json`.
5. توليد صوت MP3 لاحقاً عبر SILMA TTS أو خدمة خارجية محلية.
6. لاحقاً: صور SDXL + مونتاج MP4.
7. لاحقاً جداً: فيديو AI لمشاهد قصيرة فقط.

## طريقة البداية على Windows

```powershell
cd D:\Coding
Expand-Archive .\ai-story-studio-win.zip -DestinationPath .\
cd .\ai-story-studio-win
code .\ai-story-studio.code-workspace
```

## قبل تشغيل Codex
اقرأ بالترتيب:

1. `docs/00_START_HERE.md`
2. `docs/AI_AGENT_RULES.md`
3. `docs/CODER_TOOL_SOP.md`
4. `docs/CODEX_IMPLEMENTATION_SOP.md`
5. `docs/ARCHITECTURE.md`
6. `docs/API_CONTRACTS.md`
7. `docs/CURRENT_STAGE_SUMMARY.md`

## قبل تشغيل Gemini / Antigravity Review
استخدم:

`prompts/GEMINI_REVIEW_PROMPT.md`

## قبل تشغيل Codex لتنفيذ أول مرحلة
استخدم:

`prompts/CODEX_START_IMPLEMENTATION_PROMPT.md`

## ضبط Ollama
انسخ `.env.example` إلى `.env` ثم عدّل:

```env
OLLAMA_BASE_URL=http://YOUR_OLLAMA_IP:11434
OLLAMA_MODEL=deepseek-r1:7b
```

لا تضع أسرار حقيقية داخل Git.

## Phase 0.1 — التشغيل المحلي

بعد ضبط `.env` المحلي، شغّل:

```powershell
$env:PYTHONIOENCODING="utf-8"; python scripts/check_utf8.py
docker compose config
docker compose up --build
```

الروابط:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8810`
- Health: `http://localhost:8810/health`

Phase 0.1 يدعم فقط: اختبار Ollama، تحسين القصة، تقسيم المشاهد، وتحميل `scenes.json`.
