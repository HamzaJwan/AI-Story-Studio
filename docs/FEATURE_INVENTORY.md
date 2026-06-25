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
| ComfyUI + SDXL | Technical PASS | Product quality approval pending |
| Image continuity workflows | Researched/planned | Not benchmarked as product workflow |
| Video/WanGP | Planned only | Not started |

## Planned / Not Started

| Feature | Planned Phase |
|---|---|
| Unified job progress model | Expanded later, no Phase 1.5 foundation work started |
| Image worker bridge | Phase 2.1 after quality approval |
| Story scene images | Phase 2.2 |
| Character/location/object continuity | Phase 2.3 |
| Image style presets | Phase 2.4 |
| Separate Image Studio | Phase 2.5 |
| Long-story image batching | Phase 2.6 |
| Project Timeline View | Phase 2.7 |
| Project Asset Library | Phase 2.7 |
| Quality Review Board | Phase 2.7 |
| Regenerate per scene | Phase 2.7 |
| Prompt / Style / Story Bible Editor | Phase 2.3 / 2.4 |
| Version History / Snapshots | Later product safety feature |
| Video foundation | Phase 3.0 |
| Subtitle sidecar export (`.srt`/`.vtt`) | Phase 3.0 |
| Burned-in subtitles in MP4 | Phase 3.1 |
| Subtitle Editor | Phase 3.0 / 3.1 |
| Export presets | Phase 3.3 |
| Job Queue Dashboard | Cross-cutting after Phase 1.5 |
| Safety & Rights Checklist | Before voice/image reference expansion |
| Model / Engine Dashboard | Later ops/status feature |

## Current Recommendation

`Phase 1.5 — Audio UX Polish` is implemented and verified end-to-end. Next: either Hamza's image quality sign-off (unblocks Phase 2.1) or a Manual QA Pack / `App.tsx` cleanup pass — see `docs/NEXT_EXECUTION_PLAN.md`.
