# Remaining Features Backlog

Last updated: 2026-06-25

Status: **Future backlog only**. The current Production MVP remains complete and accepted. Nothing in this file is part of the current release unless it is later moved into a dedicated execution prompt.

## Near Future

| Feature | Goal | Why We Need It | Start When | Dependencies | Not Now / Future | Acceptance Criteria |
|---|---|---|---|---|---|---|
| Real Job Queue / Background Workers | Move long image/video/media work out of blocking HTTP requests. | Longer projects should not feel frozen, and failures need retry/cancel/history. | After Hamza final MVP QA, before scaling to long stories. | Current media endpoints, project metadata, worker status model. | Future; do not add Redis/Celery until a queue design is approved. | Jobs return `job_id`, UI can poll status, cancel/retry exists, failed jobs do not corrupt projects. |
| Project Timeline View | Show every scene as a timeline row: text, audio, image, subtitle, duration, approval, order. | This becomes the studio's main production view instead of scattered panels. | After MVP QA confirms the current 6-step workflow is stable. | Scene metadata, audio/image/video/subtitle metadata. | Future UI phase. | User can inspect all scenes, see missing assets, reorder scenes, and jump to related edit/regenerate actions. |
| Project Asset Library | Show all project files: audio, images, video, subtitles, `scenes.json`, exports. | Generated assets should be discoverable without opening ZIP/folders. | After timeline metadata is stable. | Project storage, media endpoints, export metadata. | Future UI phase. | Assets have preview/download/regenerate links and are grouped by scene/type. |
| Quality Review Board | Review each scene's text/audio/image/subtitle before final video/export. | Technical PASS is not product-quality PASS; Hamza needs approve/retry notes. | Before advanced video/export polish. | Timeline, asset library, review state in project JSON. | Future product QA phase. | Each scene can be approved/rejected/retried with notes and warnings. |
| Ken Burns / Better Video Assembly | Improve current ffmpeg video with pan/zoom/fades/crossfades. | Gives more watchable videos without heavy AI motion/GPU. | After current static-image MP4 is accepted. | Existing image/audio/subtitle/video pipeline, ffmpeg filters. | Future; no AI video models required. | MP4 exports with optional transitions, readable timing, and no broken Arabic subtitles. |

## Mid Future

| Feature | Goal | Why We Need It | Start When | Dependencies | Not Now / Future | Acceptance Criteria |
|---|---|---|---|---|---|---|
| Advanced Image Continuity | Move beyond prompt-only continuity using references/seeds/IPAdapter/ControlNet benchmarks. | Prevent character/location drift across scenes. | After image quality is accepted as worth improving. | ComfyUI lab, reference-image safety rules, benchmark plan. | Future isolated benchmark first. | Same character/location remains visually stable across at least 6 scenes in a test story. |
| Separate Image Studio | Add a separate prompt-to-image/design workspace outside story flow. | Users may need posters, certificates, marketing/social images, and reference edits. | After story-scene image flow is stable. | Image worker, safety checklist, asset storage. | Future; do not mix with story workflow yet. | Standalone images can be generated, previewed, downloaded, and stored separately from scene images. |
| Advanced Subtitle Editor | Edit subtitle text/timing/style and optionally burn subtitles into MP4. | Current SRT/VTT is basic and scene-level only. | After basic video assembly is accepted. | Subtitle export, video preview, ffmpeg subtitle rendering. | Future video polish phase. | User can edit SRT/VTT timing/text, preview over video, export sidecar and burn-in captions safely. |
| Export Presets | Export for YouTube 16:9, TikTok/Reels 9:16, Square 1:1, Presentation 16:9. | Real publishing needs platform-specific dimensions/bitrate/subtitle choices. | After video assembly and subtitle editor are stable. | Video renderer, subtitle styling, asset library. | Future export phase. | User selects a preset and receives expected dimensions/files without corrupting the project. |
| Prompt / Story Bible Editor | Dedicated editor for genre, tone, characters, locations, visual rules, forbidden changes, narration style. | Current bibles exist but need a clearer editing surface before advanced media generation. | Before advanced continuity or long stories. | Project schema fields, style presets, prompt builders. | Future UX phase. | User can review/edit story bible fields and see how they affect scene/image prompts. |
| Style Preset System Expansion | Add richer style templates: portrait, mixed styles, social/marketing variants, stronger prompt templates. | Current presets are useful but basic. | After image quality review identifies useful styles. | Image prompt builder, style preset endpoint. | Future prompt phase. | Presets are documented, selectable, and produce visibly different but controlled outputs. |
| Voice Expansion | Evaluate more voices/engines with safety and licensing: AllTalk, SILMA retry, Arabic/English voices. | Piper Arabic Kareem works, but the product needs more voice choices later. | After current audio UX is accepted and safety rules are in place. | TTS worker, benchmark matrix, consent/licensing checklist. | Future benchmark first. | Voice list comes from real worker capabilities; no celebrity/cloned voices without consent. |
| Version History / Snapshots | Store project snapshots before major changes. | Prevent accidental loss after improve/split/edit/generate operations. | Before large editing workflows become common. | Project JSON storage, snapshot retention policy. | Future safety feature. | User can restore or compare snapshots without touching generated media unexpectedly. |
| Project Templates | Add ready templates for children, horror, documentary, military, marketing, certificates, product ads. | Helps non-technical users start faster with consistent prompts/styles/export presets. | After prompt/story bible structure stabilizes. | Genre prompts, style presets, export presets. | Future content UX phase. | Templates create projects with sensible default prompts/styles and remain editable. |
| Safety & Rights Checklist | Capture consent/licensing before reference faces, voices, music, child images, celebrity likenesses. | Prevent unsafe or rights-unclear media workflows. | Before voice cloning, reference-image workflows, music/SFX, or public sharing. | Asset metadata, upload/reference flows. | Future compliance gate. | User must confirm rights/source before restricted media is used. |

## Later

| Feature | Goal | Why We Need It | Start When | Dependencies | Not Now / Future | Acceptance Criteria |
|---|---|---|---|---|---|---|
| AI Motion / Real Video Lab | Benchmark WanGP/Wan, AnimateDiff, SVD, or ComfyUI video workflows on one image-to-video clip. | Current video is ffmpeg assembly, not Veo-style motion. | Only after better ffmpeg video and image quality are accepted. | AI Server GPU budget, isolated lab, benchmark protocol. | Later lab only; no product integration before PASS. | One scene clip renders on RTX 4060 Ti with time/VRAM/quality recorded. |
| Music / Sound Effects | Add background music, SFX, ducking, volume mixing, mute/enable options. | Makes videos feel more complete when rights-safe audio exists. | After video export presets and safety checklist. | Rights checklist, asset library, ffmpeg audio mixing. | Later. | User can add rights-safe music/SFX and export balanced audio without drowning narration. |
| Local AI Assistant Lab | Evaluate Open WebUI/Ollama as a local ChatGPT/Gemini-like assistant with project docs/RAG. | Useful for story help, prompt fixes, and project Q&A without building chat from scratch. | After Production MVP is stable; as a lab first. | Existing Open WebUI, Ollama models, project docs, RAG benchmark. | Later lab; do not add custom chat app first. | Assistant answers project-doc questions with sources and refuses when evidence is missing. |
| Model / Engine Dashboard | Show Ollama/TTS/Image/ComfyUI/GPU/model/benchmark status and last successful job. | Operators need to know what is available without exposing internal URLs to the browser. | After worker/job metadata is standardized. | Health endpoints, benchmark records, backend-only proxy. | Later ops feature. | Dashboard shows status and benchmark notes without leaking AI Server URLs/secrets. |
| Public Deployment / Auth | Add users, permissions, ownership, storage limits, secure reverse proxy. | Needed only if this becomes multi-user/public. | Only after explicit product decision. | Auth design, DB/storage strategy, security review. | Not now. | Users/projects are isolated, authenticated, and storage/security limits are enforced. |

## Recommended First 5 After Final MVP QA

1. Real Job Queue / Background Workers.
2. Project Timeline View.
3. Project Asset Library.
4. Quality Review Board.
5. Ken Burns / Better Video Assembly.

These are the most realistic next steps because they improve the already-working pipeline without requiring new models, new GPU-heavy AI video, or public deployment.
