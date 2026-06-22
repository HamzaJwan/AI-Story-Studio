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
    "version": "0.1.0"
  },
  "meta": {},
  "errors": []
}
```

## GET /api/ai/ollama/health

Response:

```json
{
  "data": {
    "ok": true,
    "provider": "ollama",
    "model": "deepseek-r1:7b",
    "base_url_configured": true
  },
  "meta": {},
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
        "visual_prompt_en": "Cinematic realistic scene...",
        "audio_sfx_suggestions": ["heartbeat", "night_room"],
        "duration_seconds": 35
      }
    ]
  },
  "meta": {
    "source": "ollama",
    "model": "deepseek-r1:7b",
    "limitations": ["AI output requires human review"]
  },
  "errors": []
}
```

## POST /api/story/improve-narration

Request:

```json
{
  "story_text": "النص...",
  "tone": "وثائقي عسكري هادئ",
  "preserve_meaning": true
}
```

Response:
نفس envelope مع `improved_text`.
