# Feature Inventory

Last updated: 2026-06-25

## Implemented

| Feature | Evidence | Status |
|---|---|---|
| Ollama health/config | `/health`, `/api/config`, `/api/ai/ollama/health` | Working |
| Story improvement | `POST /api/story/improve` | Working |
| Scene splitting | `POST /api/story/split-scenes` | Working |
| Project create/list/load/update/delete | `backend/app/routers/projects.py` | Working |
| Editable scene cards | `frontend/src/App.tsx` scene editor | Working |
| `scenes.json` export | `GET /api/projects/{project_id}/scenes.json` and frontend download | Working |
| Project ZIP export | `GET /api/projects/{project_id}/export.zip` | Working |
| TTS health bridge | `GET /api/tts/health` | Working when configured |
| Single TTS job bridge | `POST /api/projects/{project_id}/tts/jobs` | Working for current first-scene flow |
| TTS job polling | `GET /api/tts/jobs/{job_id}` | Working |
| Backend proxy audio download | `GET /api/tts/jobs/{job_id}/download/{format}` | Working |
| Generate all project audio | `POST /api/projects/{project_id}/tts/generate-all` | Working |
| Audio included in ZIP | `data/projects/{id}/audio` files included in export | Working |
| ComfyUI benchmark | `deploy/ai-server/comfyui-lab` | Technical PASS |
| Voice/language catalog | `GET /api/tts/voices` (Phase 1.5) | Working — static honest catalog, no invented options |
| Per-scene saved audio metadata | `GET /api/projects/{project_id}/audio` (Phase 1.5) | Working — verified on a real 6-scene project |
| Per-scene saved audio playback | `GET /api/projects/{project_id}/audio/{scene_id}` (Phase 1.5) | Working — real `<audio>` + download, no ZIP needed |
| Full-story playback | `GET /api/projects/{project_id}/audio/final_story.wav` (Phase 1.5) | Working — computed on demand, verified valid WAV |
| Audio Studio UX | Voice/language selectors, status copy, per-scene + full-story players in `App.tsx` | Working |
| Image worker bridge | `GET /api/images/health`, `POST .../images/jobs`, `GET /api/images/jobs/{id}`, `.../download` (Phase 2.1) | Working — backend-proxied to ComfyUI, verified with real generated PNGs |
| Story scene images | `POST .../images/scenes/{id}/generate`, `.../generate-all`, `GET .../images`, `.../images/{id}` (Phase 2.2) | Working — persisted, included in export.zip |
| Continuity bibles + style presets | `Project.story_style_bible/character_bible/location_bible/object_bible/negative_prompt/style_preset`, `GET /api/images/style-presets` (Phase 2.3) | Working — verified fix for a real style-drift bug |
| Video assembly | `POST .../video/render`, `GET .../video`, `.../video/download` (Phase 3.0) | Working — ffmpeg MP4, verified frame-by-frame |
| Subtitle export | `GET .../subtitles.srt`, `.../subtitles.vtt` (Phase 3.0/3.1) | Working — timing matches the rendered video exactly |

## Implemented But Needs UX Polish

| Feature | Current Gap | Recommended Phase |
|---|---|---|
| Job progress | Basic status exists; no percentage/ETA/scene-by-scene project progress | Shared job/progress model, later |

## Benchmark-Only

| Area | Status | Notes |
|---|---|---|
| SILMA | PASS as isolated lab; blocked in worker by network during later attempt | Keep isolated, do not force into product |
| Piper | PASS in TTS worker | Current default practical engine |
| AllTalk/XTTS | Candidate | Needs real benchmark before product use |
| ComfyUI + SDXL | PASS, product-integrated | Quality `CANDIDATE`, not final product sign-off |
| Image continuity workflows | Tier 1 (prompt-only) implemented and verified | Pixel-level/face-locked continuity is a later tier |
| WanGP / image-to-video | Planned only | Not started, stays an isolated lab benchmark (Phase 3.2) |

## Planned / Not Started

| Feature | Planned Phase |
|---|---|
| Unified job progress model | Expanded later, no foundation work started |
| Separate Image Studio | Phase 2.5 |
| Long-story image batching | Phase 2.6 |
| Project Timeline View | Phase 2.7 |
| Project Asset Library | Phase 2.7 |
| Quality Review Board | Phase 2.7 |
| Regenerate per scene (beyond images) | Phase 2.7 |
| Version History / Snapshots | Later product safety feature |
| Burned-in subtitles in MP4 / styling presets | Phase 3.1 |
| Subtitle Editor / word-level alignment | Phase 3.0 / 3.1 |
| Export presets | Phase 3.3 |
| Job Queue Dashboard | Cross-cutting after Phase 1.5 |
| Safety & Rights Checklist | Before voice/image reference expansion |
| Model / Engine Dashboard | Later ops/status feature |
| Local AI Assistant Lab | Phase 4.0 |
| Chat model benchmark | Phase 4.1 |
| Project Knowledge/RAG setup | Phase 4.2 |
| Web search benchmark | Phase 4.3 |
| Vision chat benchmark | Phase 4.4 |
| Story Studio assistant tools | Phase 4.5 |

## Current Recommendation

The Studio MVP pipeline (story → scenes → audio → scene images → continuity → video → subtitles → export) is implemented and verified end-to-end on a real fresh project. Next: Hamza's own manual QA pass (`docs/MANUAL_QA_CHECKLIST.md`), then a product call on which roadmap track to pursue next (Phase 2.7 Production Studio Foundations, Phase 3.1 video polish, or Phase 4.x assistant lab).
