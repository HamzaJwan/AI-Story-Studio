# Current Stage Summary

## Current Stage

**Stage:** Phase 3.0 — Video Assembly MVP

**Status:** ✅ Implemented and verified — real MP4 rendered from real scene images + audio, frame visually inspected.

**Recommendation:** Continuing the Studio MVP Autopilot round. Next: Phase 3.0/3.1 Subtitle Export MVP (.srt/.vtt).

## What Changed in Phase 3.0

- `backend/Dockerfile` now installs `ffmpeg` (apt, `--no-install-recommends`) — first time the backend image needed a system dependency beyond Python packages.
- New `backend/app/routers/videos.py`: `POST /api/projects/{id}/video/render` (per-scene H.264 segments via `ffmpeg -loop 1 -i image.png -i audio.wav -t duration ...`, concatenated with the concat demuxer, `-c copy`, no re-encode), `GET /api/projects/{id}/video` (metadata), `GET /api/projects/{id}/video/download` (streams the MP4).
- `storage.py` gained `project_video_dir()`, `get_video_path()`, `get_video_metadata()`/`save_video_metadata()` — video metadata lives in a small sidecar `metadata.json` next to the file rather than new `Project` schema fields, since it's one derived artifact per project, not per-scene data.
- `build_export_zip()` now includes `video/final_story.mp4` when present; `metadata.json` gained `video_included`/`video_limitations`.
- Frontend: a "تجميع الفيديو" panel — render button, status message (including which scenes were skipped and why), `<video>` preview + download.

## Verified End-to-End (real, not simulated)

- Rendered a real 6-scene project (all scenes had both image and audio) → `6/6` included, `0` skipped, 52s duration, ~1.05 MB MP4, rendered in ~18 seconds.
- `ffprobe` on the real file confirms: H.264 video stream (768×768) + AAC audio stream, duration `52.046016s` — matches the API's reported duration.
- Extracted a real frame at `t=2s` and **visually inspected** it: the actual scene 01 image (storyteller at a window), confirming the video genuinely contains the right content, not just a correctly-shaped file.
- Rendered a mostly-empty project (only 1 of 6 scenes had a saved image) → `included: ["03"]`, 5 scenes correctly skipped with `"no saved image for this scene"` reasons, 6s duration.
- Zero-scene project → `422` with a clear message, no crash.
- `export.zip` for the full project → 18 files (audio + images + video together), correct `video_included: true`.
- Path traversal / address leakage grep on all video responses → clean. Video metadata survives a backend container restart.
- Full regression: `check_utf8`, `compileall`, `docker compose config`, frontend build, smoke test — all pass.

## Do Not Do Yet

- لا فيديو بالذكاء الاصطناعي (WanGP/image-to-video) — هذا Phase 3.2، يبقى مخبرياً منفصلاً.
- لا انتقالات متقدمة أو بطاقات عناوين أو دمج صوت — هذا Phase 3.1.
- لا ترجمات مدمجة في الفيديو بعد (الترجمات نفسها Milestone F القادم).
