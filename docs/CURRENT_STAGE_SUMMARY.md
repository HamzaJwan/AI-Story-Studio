# Current Stage Summary

## Current Stage

**Stage:** Phase 2.3 — Continuity Foundation MVP

**Status:** ✅ Implemented and verified — the style-drift bug found in Phase 2.2 is now fixed with real evidence, not just a code review.

**Recommendation:** Continuing the Studio MVP Autopilot round. Next: Phase 3.0 Video Assembly MVP (ffmpeg-based, not AI video).

## What Changed in Phase 2.3

- `Project` gained continuity fields: `story_style_bible`, `character_bible`, `location_bible`, `object_bible`, `negative_prompt`, `style_preset` (default `cinematic_realistic`) — additive, set via the existing `POST`/`PUT /api/projects` endpoints (no new endpoint needed; the generic `exclude_unset` merge in `storage.update_project()` already handled it once the schema fields existed).
- `backend/app/routers/images.py` gained `STYLE_PRESETS` (6 presets), `build_scene_image_prompt()`, `build_negative_prompt()` — every image generation path (single job, per-scene generate, generate-all) now assembles the prompt from style preset + story bible + scene text + character/location/object bibles, instead of sending the raw `scene.image_prompt_en` alone.
- New `GET /api/images/style-presets` so the frontend doesn't hardcode a second copy of the preset list.
- Frontend: a "ضبط الاستمرارية البصرية" panel (style preset selector + 5 bible/negative-prompt text areas) inside the Image Studio section, saved together with the rest of the project via the existing "حفظ المشروع" button.

## Real Fix, Verified (not just code review)

Phase 2.2 found that scene 03 of a real project rendered in a visibly different art style (illustrative/engraving) from scenes 01/02 (realistic/cinematic), because no shared style was enforced. After this phase:
1. Set `character_bible` ("elderly man, short grey beard, brown wool coat") and `story_style_bible` ("warm amber lighting, 35mm film grain") on that exact project.
2. Regenerated scene 03 — the assembled `image_prompt_used` correctly chained preset + story bible + scene text + character bible.
3. Downloaded and **visually inspected** the new image: a photo-real elderly man with a grey beard in a brown wool coat, under warm amber lighting, holding a book — matching the bible text precisely. The illustrative/engraving drift was gone.
4. Ran `generate-all` again on all 6 scenes with continuity active — `6/6` succeeded.

## Verified End-to-End (real, not simulated)

- `GET /api/images/style-presets` → 6 real presets.
- Existing (pre-Phase-2.3) project loads with `style_preset: "cinematic_realistic"` and empty bibles by default — no migration needed, no broken reads.
- Continuity fields persist through a backend container restart.
- Full regression: `check_utf8`, `compileall`, `docker compose config`, frontend build, smoke test — all pass.

## Do Not Do Yet

- لا فيديو (Phase 3.0) — يبدأ الآن كخطوة تالية في هذا الجولة.
- لا تثبيت وجه/شخصية بالصورة (face-lock/reference image) — هذا Tier أعلى من `IMAGE_CONTINUITY_STRATEGY.md`، خارج نطاق MVP.
- جودة الصور لا تزال `CANDIDATE`، الاستمرارية الآن أفضل لكنها نصية فقط (Tier 1)، وليست ضماناً هندسياً.
