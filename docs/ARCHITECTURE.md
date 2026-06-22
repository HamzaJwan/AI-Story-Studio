# Architecture — AI Story Studio

## High-Level Architecture

```text
Frontend React/Vite
    ↓ HTTP
Backend FastAPI
    ↓
Story Engine
    ↓
AI Provider Adapter
    ↓
Ollama API / Future providers

Backend
    ↓
File Storage under data/projects
    ↓
Phase 0 export: scenes.json
Future exports: Markdown / MP3 / MP4
```

## MVP Architecture

### Frontend
- React + Vite + TypeScript
- Tailwind CSS
- Framer Motion
- RTL Arabic UI
- شاشة واحدة في البداية:
  - Story input
  - AI actions
  - scenes result
  - generation status
  - download area later

### Backend
- FastAPI
- Pydantic contracts
- AI provider adapter
- File-based storage
- No DB in Phase 0 unless required

### AI Provider Adapter

```text
AIProvider
  health()
  generate_text(prompt, options)
  generate_json(prompt, schema_hint, options)
```

### Story Engine

```text
StoryEngine
  improve_narration_script()
  split_into_scenes()
  build_visual_prompts()    # Phase 2 — DO NOT IMPLEMENT IN PHASE 0
  prepare_tts_segments()    # Phase 1 — DO NOT IMPLEMENT IN PHASE 0
```

## Why Adapter Pattern?

حتى لا يصبح المشروع مربوطاً بـ Ollama فقط. لاحقاً يمكن إضافة:
- OpenAI
- Gemini
- Anthropic
- Local model آخر
- TTS provider (Phase 1/2/3 — DO NOT IMPLEMENT IN PHASE 0)

## Storage Model MVP

```text
data/projects/{project_id}/
  story.txt
  scenes.json
  metadata.json
```

Future Phase 1/2/3 storage — DO NOT IMPLEMENT IN PHASE 0:

```text
data/projects/{project_id}/
  narration/
  prompts/
  audio/
  images/
  video/
```

## Future Services

- SILMA TTS service — Phase 1/2/3, DO NOT IMPLEMENT IN PHASE 0
- FFmpeg worker — Phase 1/2/3, DO NOT IMPLEMENT IN PHASE 0
- ComfyUI adapter — Phase 1/2/3, DO NOT IMPLEMENT IN PHASE 0
- Whisper subtitles — Phase 1/2/3, DO NOT IMPLEMENT IN PHASE 0
- Redis/RQ for long jobs — Phase 1/2/3, DO NOT IMPLEMENT IN PHASE 0
