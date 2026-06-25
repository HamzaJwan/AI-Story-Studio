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

## Current TTS API — Phase 1.x

All TTS traffic must pass through the main backend. The browser must not call `TTS_SERVICE_URL` or the AI Server directly.

### GET /api/tts/health

Response:

```json
{
  "data": {
    "enabled": true,
    "configured": true,
    "service_url_configured": true,
    "remote_ok": true,
    "latency_ms": 12
  },
  "meta": {
    "provider": "tts-worker"
  },
  "errors": []
}
```

### POST /api/projects/{project_id}/tts/jobs

Creates a single TTS job for one scene or for the project narration text. Existing UI currently uses it mainly for the first scene.

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

Response:

```json
{
  "data": {
    "job_id": "uuid",
    "status": "queued",
    "files": []
  },
  "meta": {
    "provider": "tts-worker"
  },
  "errors": []
}
```

### GET /api/tts/jobs/{job_id}

Returns worker job status and file metadata when done.

### GET /api/tts/jobs/{job_id}/download/{format}

Streams generated job audio through the backend proxy.

### POST /api/projects/{project_id}/tts/generate-all

Generates WAV audio for all scenes, saves the files under the local project audio folder, and updates scene audio metadata.

Response:

```json
{
  "data": {
    "generated": ["01", "02"],
    "failed": [],
    "total_scenes": 2
  },
  "meta": {
    "provider": "tts-worker"
  },
  "errors": []
}
```

### Phase 1.5 — Audio UX Polish endpoints (implemented)

These are lightweight UX proxy endpoints only — they introduce no new TTS engine and never expose `TTS_SERVICE_URL` or any AI Server URL/path to the browser.

#### GET /api/tts/voices

The deployed worker has no voice-listing endpoint and currently only runs Piper with one voice, so this returns a static, honest catalog rather than inventing options. Always returns `200`, independent of `TTS_ENABLED`/connectivity (this is "what voices does the app support", not a live health check).

```json
{
  "data": {
    "voices": [
      { "voice_id": "ar_JO-kareem-medium", "label": "Arabic Kareem", "language": "ar", "engine": "piper", "default": true }
    ],
    "languages": [
      { "language": "ar", "label": "العربية", "default": true }
    ]
  },
  "meta": { "provider": "tts-worker" },
  "errors": []
}
```

#### GET /api/projects/{project_id}/audio

Per-scene and full-story saved-audio metadata. `url` values are relative paths on **this** backend (`/api/projects/...`), never `TTS_SERVICE_URL` or a filesystem path. `final_story` is only `has_audio: true` once 2+ scenes have `wav` audio (matches the `export.zip` concatenation rule from Phase 1.4).

```json
{
  "data": {
    "project_id": "uuid",
    "scenes": [
      {
        "scene_id": "01",
        "has_audio": true,
        "audio_format": "wav",
        "audio_bytes": 425004,
        "audio_generated_at": "2026-06-24T22:37:29.255028+00:00",
        "url": "/api/projects/{project_id}/audio/01"
      }
    ],
    "final_story": { "has_audio": true, "url": "/api/projects/{project_id}/audio/final_story.wav" }
  },
  "meta": {},
  "errors": []
}
```

Returns `404` with the standard error envelope if `project_id` does not exist.

#### GET /api/projects/{project_id}/audio/{scene_id}

Streams saved scene audio (`audio/wav` or `audio/mpeg`) directly from local disk through the backend. The path is resolved and verified to stay inside the project's audio directory before being read (path-traversal safe); an unknown/invalid `scene_id` or missing file returns `404`, never a directory listing or error leaking a real path.

#### GET /api/projects/{project_id}/audio/final_story.wav

Streams the same raw-WAV concatenation used by `export.zip`, computed on demand (not cached as a separate file) so it always matches current scene audio. Returns `404` if fewer than 2 scenes have `wav` audio.

#### Existing job endpoints — filesystem path hygiene

`GET /api/tts/jobs/{job_id}` and the job object returned by `POST /api/projects/{project_id}/tts/jobs` now strip the worker's internal container path (`files[].path`, e.g. `/workspace/data/jobs/...`) before returning to the browser — only `format`/`bytes` remain. The endpoint shape and the existing download flow (`GET /api/tts/jobs/{job_id}/download/{format}`) are otherwise unchanged.

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

## Phase 0.4 Story Package Export (extended in Phase 1.4)

### GET /api/projects/{project_id}/export.zip

Returns a downloadable ZIP archive (`application/zip`) containing the full project package:

- `story.txt` — `original_story`, UTF-8 plain text.
- `improved_story.txt` — `improved_story`, UTF-8 plain text. May be empty.
- `scenes.json` — identical payload to `GET /api/projects/{project_id}/scenes.json` (now includes each scene's `audio_generated_at`/`audio_bytes`/`audio_format` if audio exists).
- `audio/scene_{scene_id}.wav` — one file per scene that has generated audio (Phase 1.4). Omitted entirely for scenes/projects with no audio yet — does not break the original ZIP shape.
- `audio/final_story.wav` — raw WAV concatenation (scene order) of all scene audio, **only when 2+ scenes have `wav` audio**. No MP3/ffmpeg dependency in the backend image; convert externally if MP3 is needed (documented in `metadata.json.audio_limitations`).
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
  "phase": "1.4",
  "audio_scene_count": 6,
  "audio_limitations": ["final_story.wav is a raw WAV concatenation ... convert externally if MP3 is needed."]
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
- **Phase 1.3:** the backend derives `text` itself from storage (`scene.narration_ar` for `mode="scene"`, or all scenes' `narration_ar` joined with newlines for `mode="project"`) and sends it to the worker — the frontend never sends raw text. Returns `422` if the resulting text is empty, or if `mode="project"` and the project has no scenes.
- Returns `503` with `{"detail": "TTS service is not configured."}` if TTS is not enabled/configured.
- Returns `404` if `project_id` or `scene_id` does not exist.
- Returns `502` if the configured `tts-worker` is unreachable or errors.
- If configured and reachable, proxies the request body (including the derived `text`) to `{TTS_SERVICE_URL}/api/tts/jobs` and returns its JSON response as `data`.

### GET /api/tts/jobs/{job_id}

- Returns `503` with `{"detail": "TTS service is not configured."}` if TTS is not enabled/configured.
- Otherwise proxies to `{TTS_SERVICE_URL}/api/tts/jobs/{job_id}` and returns its JSON response as `data`.

### GET /api/tts/jobs/{job_id}/download/{format}

Phase 1.3. Proxies the raw audio bytes from `{TTS_SERVICE_URL}/api/tts/jobs/{job_id}/download/{format}` with the worker's `Content-Type` (`audio/wav` or `audio/mpeg`) preserved. Returns `503` if not configured, `502` if the worker errors. The frontend's `<audio>` player and download link point directly at this backend URL — the browser never talks to `TTS_SERVICE_URL` or the AI Server directly.

### POST /api/projects/{project_id}/tts/generate-all

Phase 1.4. Synchronously generates real audio for **every scene** in the project (one worker job per scene, polled to completion in sequence — up to ~2 minutes per scene before giving up on that scene and moving to the next). Each successful scene's WAV is downloaded and saved under `data/projects/{project_id}/audio/scene_{scene_id}.wav`, and the scene's `audio_generated_at`/`audio_bytes`/`audio_format` fields are persisted to the project JSON.

- Returns `503` if not configured, `404` if the project doesn't exist, `422` if the project has no scenes.
- Scenes with empty narration are skipped (reported in `failed`, not a hard error for the whole batch).
- A single scene's worker failure or timeout does not stop the rest of the batch.

Response:

```json
{
  "data": {
    "generated": ["01", "02", "03", "04", "05", "06"],
    "failed": [],
    "total_scenes": 6
  },
  "meta": { "provider": "tts-worker" },
  "errors": []
}
```

### TTS Worker Contract (external service — `PASS`, running on AI Server)

The `tts-worker` service is implemented at `deploy/ai-server/tts-worker/` (Phase 1.2), deployed separately on the AI Server (`docker compose up -d`, port 8851). Verified 2026-06-24 with real generated WAV files via the default `ENGINE=piper` (`ar_JO-kareem-medium`, MIT-licensed voice) — see `docs/TTS_ENGINE_BENCHMARK_MATRIX.md` for the full benchmark record. `ENGINE=silma` is also implemented but currently `BLOCKED` on this deployment (HuggingFace model download stalled due to network conditions, not a code defect). It exposes:

```text
GET  /health
POST /api/tts/jobs                       {"text": "...", "voice_id": null, "speed": 1.0, "format": "wav"}
GET  /api/tts/jobs/{job_id}
GET  /api/tts/jobs/{job_id}/files
GET  /api/tts/jobs/{job_id}/download/{format}
```

Note: this worker's job body takes raw `text` directly — it has no concept of `project_id`/`scene_id`. The backend (`backend/app/routers/tts.py`, Phase 1.3) derives `text` from the project/scene before calling it.

This app's backend only proxies to these endpoints via `TTS_SERVICE_URL`. The worker itself is out of scope for Phase 1.1.
