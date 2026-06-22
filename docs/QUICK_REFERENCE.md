# Quick Reference

## Windows Start

```powershell
cd D:\Coding\ai-story-studio-win
code .\ai-story-studio.code-workspace
Copy-Item .env.example .env
notepad .env
python scripts/check_utf8.py
docker compose config
```

## AI Review

```text
Use prompts/GEMINI_REVIEW_PROMPT.md
```

## Codex Start

```text
Use prompts/CODEX_START_IMPLEMENTATION_PROMPT.md
```

## Ollama Config

```env
OLLAMA_BASE_URL=http://YOUR_OLLAMA_IP:11434
OLLAMA_MODEL=deepseek-r1:7b
```

## Phase Rules

```text
Phase 0: Ollama + scenes JSON
Phase 1: Audio MP3
Phase 2: Images + MP4
Phase 3: AI video clips experimental
```
