# Remaining Features Backlog

Last updated: 2026-06-26

Status: **Future backlog only**. Production Studio RC2 (Phase 2.7 Production Studio
Foundations, plus the long-story-improve fix) is complete and accepted -- see
`docs/PRODUCTION_STUDIO_RC2_REPORT.md`. The five items formerly listed here as "Near
Future" (Job Queue, Timeline View, Asset Library, Review Board, Ken Burns video) are
now implemented and removed from this table. Nothing in this file is part of the
current release unless it is later moved into a dedicated execution prompt.

## Near Future

| Feature | Goal | Why We Need It | Start When | Dependencies | Not Now / Future | Acceptance Criteria |
|---|---|---|---|---|---|---|
| Job system crash recovery / cancel endpoint | The RC2 job system has no stale-job sweep and no cancel endpoint. | A backend restart mid-job leaves the job record stuck on `running` forever. | If multi-user or longer-running jobs become common. | `backend/app/jobs.py`. | Future hardening; still local JSON, no Redis/Celery. | A job started before a restart resolves to `failed` or is detectable as stale, not stuck `running` indefinitely. |
| Advanced Image Continuity | Move beyond prompt-only continuity using references/seeds/IPAdapter/ControlNet benchmarks. | Prevent character/location drift across scenes; RC2's prompt preview only shows what's sent, doesn't add real continuity. | After image quality is accepted as worth improving. | ComfyUI lab, reference-image safety rules, benchmark plan. | Future isolated benchmark first. | Same character/location remains visually stable across at least 6 scenes in a test story. |
| Export Presets | Export for YouTube 16:9, TikTok/Reels 9:16, Square 1:1, Presentation 16:9. | Real publishing needs platform-specific dimensions/bitrate/subtitle choices. | After RC2's Ken Burns video mode is accepted. | Video renderer (`backend/app/routers/videos.py`), subtitle styling, asset library. | Future export phase. | User selects a preset and receives expected dimensions/files without corrupting the project. |
| Advanced Subtitle Editor | Edit subtitle text/timing/style and optionally burn subtitles into MP4. | Current SRT/VTT is basic and scene-level only. | After RC2's video assembly is accepted. | Subtitle export, video preview, ffmpeg subtitle rendering. | Future video polish phase. | User can edit SRT/VTT timing/text, preview over video, export sidecar and burn-in captions safely. |

## Mid Future

| Feature | Goal | Why We Need It | Start When | Dependencies | Not Now / Future | Acceptance Criteria |
|---|---|---|---|---|---|---|
| Style Preset System Expansion | Add richer style templates: portrait, mixed styles, social/marketing variants, stronger prompt templates. | Current presets are useful but basic. | After image quality review identifies useful styles. | Image prompt builder, style preset endpoint. | Future prompt phase. | Presets are documented, selectable, and produce visibly different but controlled outputs. |
| Voice Expansion | Evaluate more voices/engines with safety and licensing: AllTalk, SILMA retry, Arabic/English voices. | Piper Arabic Kareem works, but the product needs more voice choices later. | After current audio UX is accepted and safety rules are in place. | TTS worker, benchmark matrix, consent/licensing checklist. | Future benchmark first. | Voice list comes from real worker capabilities; no celebrity/cloned voices without consent. |
| Version History / Snapshots | Store project snapshots before major changes. | Prevent accidental loss after improve/split/edit/generate operations. | Before large editing workflows become common. | Project JSON storage, snapshot retention policy. | Future safety feature. | User can restore or compare snapshots without touching generated media unexpectedly. |
| Project Templates | Add ready templates for children, horror, documentary, military, marketing, certificates, product ads. | Helps non-technical users start faster with consistent prompts/styles/export presets. | After prompt/story bible structure stabilizes. | Genre prompts, style presets, export presets. | Future content UX phase. | Templates create projects with sensible default prompts/styles and remain editable. |

## Later

| Feature | Goal | Why We Need It | Start When | Dependencies | Not Now / Future | Acceptance Criteria |
|---|---|---|---|---|---|---|
| AI Motion / Real Video Lab | Benchmark WanGP/Wan, AnimateDiff, SVD, or ComfyUI video workflows on one image-to-video clip. | Current video is ffmpeg assembly (including RC2's Ken Burns), not Veo-style motion. | Only after better ffmpeg video and image quality are accepted. | AI Server GPU budget, isolated lab, benchmark protocol. | Later lab only; no product integration before PASS. | One scene clip renders on RTX 4060 Ti with time/VRAM/quality recorded. |
| Music / Sound Effects | Add background music, SFX, ducking, volume mixing, mute/enable options. | Makes videos feel more complete when rights-safe audio exists. | After video export presets; RC2's safety checklist already covers the rights-confirmation gate. | Asset library, ffmpeg audio mixing. | Later. | User can add rights-safe music/SFX and export balanced audio without drowning narration. |
| Local AI Assistant Lab | Evaluate Open WebUI/Ollama as a local ChatGPT/Gemini-like assistant with project docs/RAG. | Useful for story help, prompt fixes, and project Q&A without building chat from scratch. | After Production MVP is stable; as a lab first. | Existing Open WebUI, Ollama models, project docs, RAG benchmark. | Later lab; do not add custom chat app first. | Assistant answers project-doc questions with sources and refuses when evidence is missing. |
| Public Deployment / Auth | Add users, permissions, ownership, storage limits, secure reverse proxy. | Needed only if this becomes multi-user/public. | Only after explicit product decision. | Auth design, DB/storage strategy, security review. | Not now. | Users/projects are isolated, authenticated, and storage/security limits are enforced. |

## Already Done (Production Studio RC2, 2026-06-26)

These were previously listed here as backlog items and are now implemented -- see
`docs/PRODUCTION_STUDIO_RC2_REPORT.md` for verification evidence:

- Real Job Queue / Background Workers (lightweight local version, no Redis/Celery/DB).
- Project Timeline View.
- Project Asset Library.
- Quality Review Board.
- Ken Burns / Better Video Assembly.
- Separate (Simple) Image Studio.
- Prompt / Story Bible Editor polish (prompt preview + clearer helper text).
- Safety & Rights Checklist.
- Model / Engine Dashboard.

## Recommended Next After RC2 QA

1. Advanced Image Continuity (reference/seed/IPAdapter benchmark).
2. Export Presets.
3. Advanced Subtitle Editor.
4. Job system crash recovery / cancel endpoint.

These are the most realistic next steps because they improve the already-working pipeline without requiring new models, new GPU-heavy AI video, or public deployment.
