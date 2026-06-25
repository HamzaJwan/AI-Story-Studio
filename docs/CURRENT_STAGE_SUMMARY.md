# Current Stage Summary

## Current Stage

**Stage:** Phase 2.2 — Story Scene Images MVP

**Status:** ✅ Implemented and verified — per-scene image generation, persistence, export.zip inclusion, all real.

**Recommendation:** Continuing the Studio MVP Autopilot round. Milestone D (Continuity Foundation) is next, and a real, observed need for it just turned up (see below) — not a speculative feature.

## What Changed in Phase 2.2

- `Scene` schema gained image metadata fields (`image_generated_at/bytes/format/width/height/engine/seed/prompt_used`) — additive, mirrors how audio metadata was added in Phase 1.4.
- `storage.py`: `project_images_dir()`, `save_scene_image()`, `get_scenes_with_images()`, `get_scene_image_path()` — same pattern as the audio equivalents, including the same path-traversal defense.
- New endpoints: `POST /api/projects/{id}/images/scenes/{scene_id}/generate` (persisted, synchronous, doubles as "regenerate"), `POST /api/projects/{id}/images/generate-all` (sequential, continues past failures), `GET /api/projects/{id}/images`, `GET /api/projects/{id}/images/{scene_id}`.
- `build_export_zip()` now includes `images/scene_{id}.png` for every scene that has one; `metadata.json` gained `image_scene_count`/`image_limitations`.
- Frontend: per-scene saved-image list (preview, download, regenerate) populated from `GET /api/projects/{id}/images`, plus a "توليد صور كل المشاهد" button.

## Real Finding Worth Flagging

Generating scene 03 in isolation produced an image in a visibly different art style (illustrative/engraving) from scenes 01/02 (realistic/cinematic) — because nothing in the pipeline enforces a consistent style across scenes; each scene's raw `image_prompt_en` text is sent as-is, with no shared style prefix. This is **exactly** the problem `docs/IMAGE_CONTINUITY_STRATEGY.md` describes (Tier 1, prompt-only, "weak continuity"). It's real, observed evidence that Milestone D isn't speculative — it's addressing something that already happened on the very first multi-scene test.

## Verified End-to-End (real, not simulated)

- Single persisted scene generation (`scene 03`) → real 1,214,869-byte PNG, metadata persisted, streamed back through the backend and confirmed valid.
- `generate-all` on a real 6-scene project → `6/6` generated, `0` failed.
- `export.zip` for that project → 17 files (6 audio scenes + `final_story.wav` + 6 images + originals), `metadata.json` correctly reports `image_scene_count: 6`.
- Persistence survives a backend container restart (confirmed: `6/6` scenes still report `has_image: true` after rebuild).
- Path traversal attempt on `/images/{scene_id}` → `404`. Zero-scene project's `/images` and `export.zip` → both still `200`.
- Full regression: `check_utf8`, `compileall`, `docker compose config`, frontend build, smoke test — all pass. Audio endpoints unaffected.

## Do Not Do Yet

- لا فيديو (Phase 3.0) قبل معالجة مشكلة الاستمرارية المرصودة فعلياً أعلاه.
- لا تعتبر جودة الصور أو اتساقها معتمدة نهائياً — لا تزال `CANDIDATE` ومعروف أنها تفتقر للاستمرارية.
