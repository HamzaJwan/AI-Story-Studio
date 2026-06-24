# Current Stage Summary

## Current Stage

**Stage:** Phase 1.4 — Project Audio Export
**Status:** Implemented and verified with real generated audio for a full 6-scene project
**Owner:** Hamza
**Executor:** Claude
**Reviewer:** Hamza

## Implemented in Phase 1.4

- `Scene` schema gains optional `audio_generated_at` / `audio_bytes` / `audio_format` fields (additive, safe for existing stored projects).
- `ProjectStorage.project_audio_dir()` / `save_scene_audio()`: scene WAV bytes are saved to `data/projects/{project_id}/audio/scene_{scene_id}.wav` (gitignored, not committed) and the scene's audio metadata is persisted in the project JSON.
- New endpoint `POST /api/projects/{project_id}/tts/generate-all`: generates real audio for every scene (sequential worker jobs, polled to completion), skips empty narration, doesn't abort the batch on a single scene's failure.
- `build_export_zip()` extended: includes `audio/scene_{id}.wav` for every scene that has audio, plus `audio/final_story.wav` — a raw WAV concatenation (stdlib `wave`, no ffmpeg/MP3 dependency) when 2+ scenes have `wav` audio. `metadata.json` documents this as a known limitation (`audio_limitations`). Does not change the ZIP shape for projects with no audio yet.
- Frontend: "توليد صوت للمشروع" now calls `generate-all` (was previously a single concatenated-text job that was never saved/exported) and reports a real summary (`"تم توليد الصوت لـ 6 من 6 مشهد"`).
- Fixed a bug found during testing: `scenes_export()` used `model_dump()` without `mode="json"`, which crashed `export.zip` with `datetime` not JSON-serializable once scenes had `audio_generated_at` set. Fixed before commit.

## Verified end-to-end (real, not simulated)

- `POST .../tts/generate-all` on a real 6-scene project → `{"generated": ["01"..."06"], "failed": [], "total_scenes": 6}`.
- Confirmed each scene's `audio_generated_at`/`audio_bytes`/`audio_format` persisted via `GET /api/projects/{id}`.
- Downloaded `export.zip` → contains all 6 `audio/scene_XX.wav` files + `audio/final_story.wav` (2,050,092 bytes, verified as valid WAV, 46.49s, matching the sum of the 6 scenes).
- Confirmed `export.zip` still returns `200` for a project with zero scenes/no audio (no regression).
- Full regression: `check_utf8`, backend `compileall`, frontend `npm run build`, `smoke_phase0_workspace.py`, and all Phase 0.x/1.x endpoints — all pass.

## Next Action

1. Commit and push Phase 1.4.
2. Per the Controlled Autopilot instruction, proceed to Phase 2.0 (Image Benchmark Lab) — but this requires the Benchmark Gate from `docs/BENCHMARK_PROTOCOL.md` and a real engine choice; pause to assess scope before writing code.

## Do Not Do Yet

- لا صور، لا فيديو حتى الآن (التركيز انتهى من الصوت لمشهد/مشروع).
- لا SILMA فعلياً (لا يزال BLOCKED بسبب الشبكة من جلسة سابقة — يستحق إعادة محاولة لاحقاً فقط).
- لا database/auth.
