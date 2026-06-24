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

---

## Phase 0.2 Project Workspace Endpoints

Project storage uses local UTF-8 JSON files under `data/projects/`. Do not commit generated project JSON files.

### POST /api/projects

Creates a local project.

Request:

```json
{
  "title": "قصة جديدة",
  "original_story": "النص الأصلي...",
  "improved_story": "سكريبت الراوي...",
  "scenes": []
}
```

Response: `ProjectResponse` with `project_id`, `title`, `original_story`, `improved_story`, `scenes`, `created_at`, and `updated_at`.

### GET /api/projects

Returns `{ "projects": ProjectListItem[] }` with `project_id`, `title`, `scene_count`, `created_at`, and `updated_at`.

### GET /api/projects/{project_id}

Returns one local project.

### PUT /api/projects/{project_id}

Updates `title`, `original_story`, `improved_story`, and/or `scenes`.

### DELETE /api/projects/{project_id}

Deletes one local project JSON file.

### GET /api/projects/{project_id}/scenes.json

Exports the latest edited scenes as downloadable `scenes.json`.

---

## Phase 0.4 Story Package Export

### GET /api/projects/{project_id}/export.zip

Returns a downloadable ZIP archive (`application/zip`) containing the full project package:

- `story.txt` — `original_story`, UTF-8 plain text.
- `improved_story.txt` — `improved_story`, UTF-8 plain text. May be empty.
- `scenes.json` — identical payload to `GET /api/projects/{project_id}/scenes.json`.
- `metadata.json`:

```json
{
  "project_id": "uuid",
  "title": "قصة جديدة",
  "created_at": "2026-06-24T00:00:00+00:00",
  "updated_at": "2026-06-24T00:00:00+00:00",
  "scene_count": 6,
  "total_duration_seconds": 48,
  "exported_at": "2026-06-24T00:10:00+00:00",
  "app": "AI Story Studio",
  "phase": "0.4"
}
```

Returns 404 with the standard error envelope if `project_id` does not exist.

---

## Phase 1.1 Audio Bridge MVP

This phase adds a backend connector to a future external `tts-worker` service. **No TTS engine runs inside this app.** If `TTS_ENABLED` is not `true` or `TTS_SERVICE_URL` is not set, every endpoint below reports `configured: false` (health) or returns `503` (job endpoints) — the app never crashes and never fabricates audio.

### GET /api/tts/health

Always returns `200`.

```json
{
  "data": {
    "enabled": false,
    "configured": false,
    "service_url_configured": false,
    "remote_ok": null
  },
  "meta": { "provider": "tts-worker" },
  "errors": []
}
```

When `configured: true`, the response also includes `remote_ok` (`true`/`false`, from a live `GET {TTS_SERVICE_URL}/health`) and `latency_ms`. If `remote_ok` is `false`, `errors` includes `"TTS worker is not reachable."`.

### POST /api/projects/{project_id}/tts/jobs

Request:

```json
{
  "mode": "scene",
  "scene_id": "01",
  "voice_id": null,
  "speed": null,
  "format": "wav"
}
```

- `mode`: `"scene"` or `"project"` (default `"project"`).
- `scene_id`: required when `mode` is `"scene"`; must exist in the project.
- Returns `503` with `{"detail": "TTS service is not configured."}` if TTS is not enabled/configured.
- Returns `404` if `project_id` or `scene_id` does not exist.
- Returns `502` if the configured `tts-worker` is unreachable or errors.
- If configured and reachable, proxies the request body to `{TTS_SERVICE_URL}/api/tts/jobs` and returns its JSON response as `data`.

### GET /api/tts/jobs/{job_id}

- Returns `503` with `{"detail": "TTS service is not configured."}` if TTS is not enabled/configured.
- Otherwise proxies to `{TTS_SERVICE_URL}/api/tts/jobs/{job_id}` and returns its JSON response as `data`.

### TTS Worker Contract (external service — `PASS`, running on AI Server)

The `tts-worker` service is implemented at `deploy/ai-server/tts-worker/` (Phase 1.2), deployed separately on the AI Server (`docker compose up -d`, port 8851). Verified 2026-06-24 with real generated WAV files via the default `ENGINE=piper` (`ar_JO-kareem-medium`, MIT-licensed voice) — see `docs/TTS_ENGINE_BENCHMARK_MATRIX.md` for the full benchmark record. `ENGINE=silma` is also implemented but currently `BLOCKED` on this deployment (HuggingFace model download stalled due to network conditions, not a code defect). It exposes:

```text
GET  /health
POST /api/tts/jobs                       {"text": "...", "voice_id": null, "speed": 1.0, "format": "wav"}
GET  /api/tts/jobs/{job_id}
GET  /api/tts/jobs/{job_id}/files
GET  /api/tts/jobs/{job_id}/download/{format}
```

Note: this worker's job body takes raw `text` directly — it has no concept of `project_id`/`scene_id`. Wiring real scene text through from `backend/app/routers/tts.py` (currently sent without `text`) is Phase 1.3's job, not Phase 1.2's.

This app's backend only proxies to these endpoints via `TTS_SERVICE_URL`. The worker itself is out of scope for Phase 1.1.
