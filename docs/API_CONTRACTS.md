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
    "phase": "3.1"
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
  "phase": "3.1",
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

---

## Phase 2.1 Image Worker Bridge

Connects the backend to the AI Server's ComfyUI service (`deploy/ai-server/comfyui-lab/`), now running as a persistent service (Phase 2.0's benchmark passed). The frontend never talks to `IMAGE_SERVICE_URL` directly — only the main backend does, exactly mirroring the TTS bridge's security boundary.

### GET /api/images/health

Always returns `200`. Same shape as `GET /api/tts/health`.

```json
{
  "data": { "enabled": true, "configured": true, "service_url_configured": true, "remote_ok": true, "latency_ms": 13 },
  "meta": { "provider": "image-worker" },
  "errors": []
}
```

### POST /api/projects/{project_id}/images/jobs

Creates an image generation job for one scene (derives the prompt from `scene.image_prompt_en`, already produced by Phase 0.1's scene splitting) or a raw `prompt` override.

Request:

```json
{ "scene_id": "01", "prompt": null, "width": null, "height": null, "seed": null }
```

- `scene_id`: optional; if given, must exist in the project.
- `prompt`: optional explicit override; if omitted, derived from `scene.image_prompt_en`.
- At least one of `scene_id`/`prompt` must resolve to non-empty text, or `422`.
- `width`/`height`: default `768×768` (matches the AI Server's tight real VRAM headroom — see `docs/HARDWARE_PROFILE.md`); range `256–1024`.
- Returns `503` if not configured, `404` if `project_id`/`scene_id` doesn't exist, `502` if the worker rejects the workflow or is unreachable.
- Submits a ComfyUI workflow (SDXL base, 20 steps, euler, cfg 7.0) directly to the worker's native `/prompt` API — no custom wrapper needed, unlike SILMA/Piper.

### GET /api/images/jobs/{job_id}

Polls job status by querying the worker's `/history/{job_id}`. Maps ComfyUI's response to the same `queued`/`running`/`done`/`failed` shape used by the TTS bridge.

### GET /api/images/jobs/{job_id}/download

Streams the generated PNG through the backend (`image/png`). Returns `404` if the job isn't done yet or has no output.

### Engine note

Uses the exact engine/settings recorded as `CANDIDATE` in `docs/IMAGE_QUALITY_APPROVAL_CHECKLIST.md` — technically proven, not yet a final product-quality approval.

---

## Phase 2.2 Story Scene Images MVP

Persisted per-scene image generation, building on the Phase 2.1 bridge.

### POST /api/projects/{project_id}/images/scenes/{scene_id}/generate

Synchronous (blocks until done, ~2 minute budget matching the audio `generate-all` pattern). Generates from `scene.image_prompt_en`, downloads the PNG, and saves it to `data/projects/{project_id}/images/scene_{scene_id}.png` with metadata (`image_generated_at`, `image_bytes`, `image_format`, `image_width`, `image_height`, `image_engine`, `image_seed`, `image_prompt_used`) persisted on the scene. Calling it again on a scene that already has an image regenerates and overwrites it (no separate "regenerate" endpoint needed).

### POST /api/projects/{project_id}/images/generate-all

Sequential per-scene generation (same pattern as audio's `generate-all` — **deliberately not parallel**, since the AI Server's VRAM margin is tight). Continues past a single scene's failure; returns `{"generated": [...], "failed": [...], "total_scenes": N}`.

### GET /api/projects/{project_id}/images

Per-scene image metadata, backend-relative `url` only (never a filesystem path or `IMAGE_SERVICE_URL`).

### GET /api/projects/{project_id}/images/{scene_id}

Streams the saved PNG (`image/png`). Path resolved against the project's real scene list and verified inside the project's images directory before reading (same traversal defense as the audio endpoints). Returns `404` for an unknown scene or missing file.

### export.zip changes

Now also includes `images/scene_{scene_id}.png` for every scene that has one, and `metadata.json` gained `image_scene_count` and `image_limitations` (parallel to the existing `audio_*` fields). Does not change the ZIP shape for projects with no images.

---

## Phase 2.3 Continuity Foundation MVP

Project-level fields (Tier 1, prompt-only continuity per `docs/IMAGE_CONTINUITY_STRATEGY.md`) injected automatically into every scene's image prompt -- no per-scene setup needed.

### New `Project` fields

`story_style_bible`, `character_bible`, `location_bible`, `object_bible`, `negative_prompt` (all free text, additive, default `""`), `style_preset` (default `"cinematic_realistic"`). Set via the existing `POST /api/projects` / `PUT /api/projects/{id}` — no new endpoint needed; `ProjectUpdateRequest`'s generic `exclude_unset` merge already handles them.

### GET /api/images/style-presets

```json
{ "data": { "presets": [{ "key": "cinematic_realistic", "prompt_prefix": "cinematic realistic photography, ..." }, ...] } }
```

Six presets: `cinematic_realistic`, `warm_storybook`, `anime_cartoon`, `military_documentary`, `horror_suspense`, `marketing_poster`. Source of truth lives in `backend/app/routers/images.py::STYLE_PRESETS` -- the frontend fetches this list rather than hardcoding a second copy.

### Prompt assembly

Every image generation path (`POST .../images/jobs`, `.../scenes/{id}/generate`, `.../generate-all`) now builds the prompt as: `style_preset prefix, story_style_bible, scene.image_prompt_en, "Characters: " + character_bible, "Location: " + location_bible, "Important objects: " + object_bible` (empty fields are skipped). The negative prompt sent to the worker is `project.negative_prompt` if set, else the worker's own default. The fully assembled prompt is stored as `scene.image_prompt_used` for transparency.

### Verified

Setting `character_bible`/`story_style_bible` on a real project and regenerating a scene that had previously drifted to an illustrative style produced a photo-real image of an elderly man with a grey beard and brown wool coat under warm amber lighting -- matching the bible text, confirmed by visual inspection.

---

## Phase 3.0 Video Assembly MVP

Backend-only ffmpeg pipeline (installed in `backend/Dockerfile`) that combines each scene's saved image + saved audio into one MP4. No AI video motion, no transitions beyond a hard cut, no burned-in subtitles -- those are Phase 3.1+ (`docs/VIDEO_SUBTITLES_PLAN.md`).

### POST /api/projects/{project_id}/video/render

Synchronous. For each scene, in order: skips it (with a `reason`) if it has no saved image; otherwise renders a per-scene H.264 segment (`768x768`, scene's saved image held static for `scene.duration_seconds`, muxed with the scene's saved audio if present, silent otherwise) via `ffmpeg -loop 1 -i image ...`, then concatenates all segments with ffmpeg's concat demuxer (`-c copy`, no re-encode) into `data/projects/{id}/video/final_story.mp4`.

```json
{
  "data": {
    "rendered_at": "2026-06-25T10:50:54Z",
    "included_scenes": ["01", "02", "03"],
    "skipped_scenes": [{ "scene_id": "04", "reason": "no saved image for this scene" }],
    "duration_seconds": 52,
    "video_bytes": 1051399
  }
}
```

- Returns `422` if the project has no scenes, or if every scene lacks a saved image (nothing to render).
- Returns `503` if ffmpeg is missing from the image (should not happen post-build); `502` if a render or concat step fails.
- Re-rendering overwrites the previous `final_story.mp4` (no separate "re-render" endpoint, same pattern as image regeneration).

### GET /api/projects/{project_id}/video

Metadata only: `has_video`, `url` (backend-relative download path), `duration_seconds`, `video_bytes`, `rendered_at`, `included_scenes`, `skipped_scenes`. Reads a small sidecar `metadata.json` next to the video file rather than adding per-project schema fields, since the video is a single derived artifact, not per-scene data.

### GET /api/projects/{project_id}/video/download

Streams the saved MP4 (`video/mp4`). `404` if nothing has been rendered yet.

### export.zip changes

Now also includes `video/final_story.mp4` when one exists; `metadata.json` gained `video_included`/`video_limitations`. Does not change ZIP shape for projects with no rendered video.

---

## Phase 3.0/3.1 Subtitle Export MVP

Pure, deterministic generation from data already in the project -- no external service, no job/polling needed (unlike audio/image generation). One cue per scene, timed cumulatively by `duration_seconds`, same timeline Phase 3.0's video assembly uses. No word-level alignment (out of scope for the MVP, see `docs/VIDEO_SUBTITLES_PLAN.md`).

### GET /api/projects/{project_id}/subtitles.srt

Returns `text/plain` SRT (`HH:MM:SS,mmm` timestamps), `Content-Disposition: attachment; filename="story.srt"`.

### GET /api/projects/{project_id}/subtitles.vtt

Returns `text/vtt` WebVTT (`HH:MM:SS.mmm` timestamps, `WEBVTT` header), `Content-Disposition: attachment; filename="story.vtt"`.

Both: `404` for an unknown project; a zero-scene project returns `200` with an effectively empty body (no cues), not an error. Scenes with empty `narration_ar` are skipped (no cue), without breaking the rest of the timeline.

### export.zip changes

Now always includes `subtitles/story.srt` and `subtitles/story.vtt` (generation is free, so unlike audio/images/video this isn't conditional on anything having been generated first).

---

## Production Studio RC2 (2026-06-26)

### Milestone 0 — Long Story Improve Fix

`POST /api/story/improve` now distinguishes real Ollama connection failures from
timeouts/HTTP errors (previously all three collapsed into one misleading "service
unreachable" Arabic message). Stories longer than `long_story_chunk_chars` (env
`LONG_STORY_CHUNK_CHARS`, default 6000) are split into ordered paragraph/sentence
chunks and improved sequentially, then joined -- no merge/smoothing pass afterwards.
`meta.chunk_count` reports how many chunks were used (`1` for short stories).
`GET /api/config` now also returns `long_story_chunk_chars` so the frontend doesn't
hardcode the threshold.

### Milestone A — Lightweight Job Progress Foundation

New job model (`backend/app/jobs.py`): local JSON files under `data/jobs/` (gitignored,
no DB/Redis/Celery). Fields: `job_id, project_id, job_type, status (queued/running/done/
failed/cancelled), current_step, total_steps, completed_steps, message_ar, safe_error_ar,
started_at, updated_at, finished_at, result_summary, affected_scene_ids`.

- `GET /api/jobs/{job_id}` — one job record, `404` if unknown.
- `GET /api/projects/{project_id}/jobs` — `{ "project_id", "jobs": JobRecord[] }`, newest first.
- `POST /api/projects/{project_id}/story/improve/jobs`
- `POST /api/projects/{project_id}/images/generate-all/jobs`
- `POST /api/projects/{project_id}/video/render/jobs`
- `POST /api/projects/{project_id}/tts/generate-all/jobs`

Each `/jobs` endpoint returns immediately with a queued `JobRecord`; the real work runs
in a FastAPI `BackgroundTasks` callable that updates the same record as it progresses.
The original synchronous endpoints (`/story/improve`, `/images/generate-all`,
`/video/render`, `/tts/generate-all`) are unchanged and still work for callers that
don't need progress polling. Every job runner has a catch-all exception handler that
marks the job `failed` with a generic `safe_error_ar` so a bug can never leave a job
stuck on `running` forever.

### Milestone D — Quality Review Board (schema only, no new endpoint)

`Scene` gained `review_status` (`pending`/`approved`/`needs_retry`/`rejected`, default
`pending`), `review_notes` (free text), `review_updated_at`. Set via the existing
`PUT /api/projects/{id}` (send the full `scenes` array back, same pattern as any other
scene edit) -- no dedicated review endpoint, no assets are ever deleted by a review
status change.

### Milestone E — Ken Burns / Better Video Assembly

`Project` gained `video_mode` (`static` default, or `ken_burns`) and `video_transition`
(`none` default, or `fade`). `POST /api/projects/{id}/video/render` (and its `/jobs`
variant) read these from the project and apply them per segment:

- `ken_burns`: ffmpeg `zoompan` filter, slow zoom-in capped at 1.15x, deterministic frame
  count from the segment's real duration. Still ffmpeg-only -- no AI video model.
- `fade`: a short fade-in/fade-out *within* each segment (not a true crossfade between
  segments, since the concat step still uses the lossless `-c copy` demuxer). Documented
  as a deliberate low-risk simplification.

The render response/metadata and `GET /api/projects/{id}/video` both gained
`video_mode`/`video_transition` fields reporting what was actually used. The Milestone 0
duration-sync guarantee (rendered duration ≈ sum of real per-scene audio durations) holds
for every mode -- verified with a synthetic 6-scene `ken_burns`+`fade` render in
`scripts/test_ken_burns_video.py`.

### Milestone F — Prompt Preview

`GET /api/projects/{project_id}/images/scenes/{scene_id}/prompt-preview` — read-only,
returns `{ "scene_id", "prompt", "negative_prompt" }`, the exact text `build_scene_image_prompt()`
would send to the image worker, without spending a real generation job. `404` if the
project or scene doesn't exist.

### Milestone G — Simple Image Studio

`POST /api/images/standalone/jobs` — single prompt in, one image job out, no project/scene
attachment, no continuity bibles mixed in.

Request:

```json
{ "prompt": "a small red apple on a white table", "style_preset": "cinematic_realistic", "negative_prompt": "", "width": 768, "height": 768, "seed": null }
```

Response: `{ "job_id", "status": "queued", "prompt" }`. Polling and download reuse the
already-existing project-agnostic `GET /api/images/jobs/{job_id}` and
`GET /api/images/jobs/{job_id}/download`. `503` if the image service isn't configured.

### Milestone H — Safety & Rights Checklist (schema only, no new endpoint)

`Project` gained `safety_source_type` (`own_content`/`licensed`/`generated`/`unknown`,
default `unknown`), `safety_consent_confirmed` (`yes`/`no`/`not_applicable`, default
`not_applicable`), `safety_rights_notes` (free text), `safety_applies_to` (list of
`voice`/`image_reference`/`music_sfx`/`person_likeness`). Set via the existing
`POST /api/projects` / `PUT /api/projects/{id}`. Purely informational -- never blocks
generation or export.

### Milestone I — Model/Engine Status Dashboard

`GET /api/system/status` aggregates the existing per-provider health checks:

```json
{
  "data": {
    "ollama": { "ok": true, "model": "qwen2.5:7b", "latency_ms": 42 },
    "tts": { "enabled": true, "configured": true, "remote_ok": true, "latency_ms": 12 },
    "image": { "enabled": true, "configured": true, "remote_ok": true, "latency_ms": 13 },
    "ffmpeg": { "available": true },
    "benchmark_notes_doc": "docs/IMAGE_QUALITY_APPROVAL_CHECKLIST.md"
  }
}
```

No IPs, `.env` values, or container paths -- every field was already safe to expose
before this endpoint existed (each provider's own `health()` already strips its URL
down to booleans/latency); this endpoint only combines three existing calls into one.
