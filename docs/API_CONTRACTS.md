# API Contracts — MVP

## General Envelope

كل endpoint مهم يرجع:

```json
{
  "data": {},
  "meta": {
    "source": "local",
    "limitations": []
  },
  "errors": []
}
```

## GET /health

Response:

```json
{
  "data": {
    "status": "ok",
    "app": "AI Story Studio",
    "phase": "0.1"
  },
  "meta": {},
  "errors": []
}
```

## GET /api/config

Response:

```json
{
  "data": {
    "provider": "ollama",
    "model": "qwen2.5:7b",
    "ollama_configured": true
  },
  "meta": {},
  "errors": []
}
```

لا يرجع `OLLAMA_BASE_URL` كاملاً.

## GET /api/ai/ollama/health

Response:

```json
{
  "data": {
    "ok": true,
    "provider": "ollama",
    "model": "qwen2.5:7b",
    "base_url_configured": true,
    "latency_ms": 123
  },
  "meta": {},
  "errors": []
}
```

## POST /api/ollama/test

Response:

```json
{
  "data": {
    "connected": true,
    "latency_ms": 123,
    "model": "qwen2.5:7b"
  },
  "meta": {
    "provider": "ollama"
  },
  "errors": []
}
```

## POST /api/story/improve

Request:

```json
{
  "story_text": "النص...",
  "tone": "عسكري هادئ",
  "language": "ar"
}
```

Response:

```json
{
  "data": {
    "improved_text": "..."
  },
  "meta": {
    "provider": "ollama",
    "model": "qwen2.5:7b"
  },
  "errors": []
}
```

## POST /api/story/split-scenes

Request:

```json
{
  "title": "المسرح لي",
  "story_text": "النص الكامل...",
  "target_scenes": 7,
  "tone": "راوي عربي عسكري هادئ ومؤثر"
}
```

Response:

```json
{
  "data": {
    "project_id": "uuid",
    "story_title": "المسرح لي",
    "scenes": [
      {
        "scene_id": "01",
        "title_ar": "ليلة الأرق",
        "narration_ar": "نص الراوي...",
        "visual_description_ar": "وصف بصري...",
        "image_prompt_en": "Cinematic realistic scene...",
        "duration_seconds": 8
      }
    ]
  },
  "meta": {
    "provider": "ollama",
    "model": "qwen2.5:7b",
    "limitations": ["AI output requires human review"]
  },
  "errors": []
}
```

## GET /api/projects/{project_id}/scenes.json

يرجع ملف `scenes.json` المحفوظ للمشروع.
