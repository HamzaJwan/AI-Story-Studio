# Current Stage Summary

## Current Stage

**Stage:** Phase 2.0 — Image Benchmark Lab

**Status:** Technical PASS, pending Hamza quality sign-off

**Recommendation:** Start Phase 1.5 — Audio UX Polish before Phase 2.1

## Verified Product State

- Phase 0.1 is stable: Ollama connection, story improvement, scene splitting, and `scenes.json` generation work.
- Phase 0.2 is stable: local project creation, saving, loading, scene editing, and edited `scenes.json` export work.
- Phase 0.3 and 0.4 are completed: scene editing UX polish and project ZIP export are available.
- Phase 1.x audio path is functionally proven with an external AI Server worker and project audio export.
- Phase 2.0 image benchmark is technically proven: ComfyUI + SDXL generated a real PNG on the AI Server.

## Important Distinction

Phase 2.0 is a **technical** image-generation pass, not a final product-quality approval. Hamza still needs to approve the actual image quality before Phase 2.1 adds an image worker bridge or any image UI.

The strongest immediate product gap is now Audio UX: audio files are generated and exported, but the app needs clearer in-browser playback, per-scene saved audio controls, full-story playback, voice/language controls, and better job status.

## Current Gaps

- Product UI still needs a small status/phase label sync before the next implementation phase.
- Audio UX needs polish: voice/language selector, per-scene saved audio playback, full project audio playback, and clearer progress.
- Image continuity is not solved yet: character, location, object, color, and long-story consistency need their own strategy.
- Long-running audio/image/video jobs need a unified progress/status model before scaling.
- TTS/SILMA/AllTalk remain AI Server services/labs; they should not be merged into the App Server.

## Next Action

1. Start Phase 1.5 — Audio UX Polish.
2. Keep all audio traffic proxied through the backend.
3. After Audio UX polish, return to Hamza's image quality approval and Phase 2.1 planning.

## Do Not Do Yet

- Do not start Phase 2.1 before Audio UX polish and image quality sign-off.
- Do not add frontend image generation UI yet.
- Do not start video generation.
- Do not expose ComfyUI or other AI Server services directly to the browser.
