# AI Pipeline Design

## Phase 0 Pipeline

Phase 0 فقط: واجهة + Backend + Ollama + Improve Story + Split Scenes + scenes.json.

```text
User story
  ↓
Backend validates length and UTF-8
  ↓
Ollama adapter
  ↓
Story Engine prompt
  ↓
JSON extraction and validation
  ↓
scenes.json
  ↓
Frontend review
```

## Phase 1 Pipeline — Audio

Phase 1/2/3 — DO NOT IMPLEMENT IN PHASE 0.

```text
scenes.json
  ↓
narration segments
  ↓
TTS adapter
  ↓
scene_01.wav ...
  ↓
FFmpeg / pydub merge
  ↓
final.mp3
```

## Phase 2 Pipeline — Images + MP4

Phase 1/2/3 — DO NOT IMPLEMENT IN PHASE 0.

```text
scenes.json
  ↓
visual_prompts_en
  ↓
ComfyUI/SDXL manual or API
  ↓
scene images
  ↓
FFmpeg Ken Burns / transitions
  ↓
final.mp4
```

## Phase 3 Pipeline — Short AI Video

Phase 1/2/3 — DO NOT IMPLEMENT IN PHASE 0.

```text
approved image
  ↓
WanGP / Wan2.1 image-to-video
  ↓
3-5 seconds clip
  ↓
manual review
  ↓
optional inclusion in MP4
```

## Important Rule

الفيديو AI ليس أساس المنتج الآن. الأساس:
- قصة منظمة.
- سكريبت راوي قابل للمراجعة.
- مشاهد منظمة داخل `scenes.json`.
- واجهة واضحة تعرض الناتج بدون مشاكل UTF-8.
