# Advanced Feature Backlog

Last updated: 2026-06-25

This backlog merges Hamza's product ideas, Codex planning notes, and the current roadmap into one structured production-studio backlog.

The next execution phase remains **Phase 1.5 — Audio UX Polish**. Everything here is future planning unless explicitly moved into an execution prompt.

## Categories

- Implemented
- Implemented but needs UX polish
- Benchmark-only
- Near-term
- Mid-term
- Later
- Not now

## Strategic Priority

The strongest three strategic features are:

1. Project Timeline View.
2. Project Asset Library.
3. Quality Review Board.

These turn the app from “generate files” into “manage a story production”.

## Backlog Table

| Feature | Category | Proposed Phase | Priority | Dependencies | Why It Matters | Acceptance Criteria | Risks | Not In Current Phase |
|---|---|---|---|---|---|---|---|---|
| Phase 1.5 Audio UX Polish | Near-term | 1.5 | Critical | Current TTS worker path | Makes proven audio usable inside the app | Voice/language selectors, scene player, full-story player, clear status | Scope creep into new TTS engines | No new engine/image/video work |
| Project Timeline View | Mid-term | 2.7 | High | Audio UX, scene images, subtitle metadata | Central view for scene → narration → audio → image → subtitle → video segment | Shows missing assets, duration, status, warnings, review/regenerate links | Too much UI if started early | Not in Phase 1.5 |
| Project Asset Library | Mid-term | 2.7 | High | Storage metadata, generated media paths | Keeps outputs discoverable and tied to scenes | Preview/download/link assets; no generated files in Git | File cleanup and metadata drift | Not in Phase 1.5 |
| Quality Review Board | Mid-term | 2.7 | High | Audio/image/subtitle outputs | Technical PASS is not product quality PASS | Approve/retry/reject per scene with notes | Review state complexity | Not in Phase 1.5 |
| Regenerate Per Scene | Mid-term | 2.7 | High | Job system, asset library | Avoids rerunning the whole project after one bad scene | Regenerate audio/image/subtitle/prompt for one scene | Version conflicts | Not in Phase 1.5 |
| Prompt / Style / Story Bible Editor | Mid-term | 2.3 / 2.4 | High | Continuity strategy, image generation | Prevents character/location/object drift | Editable story/character/location/object/style bibles | Requires careful UX | Not in Phase 1.5 |
| Version History / Snapshots | Later | 2.7+ | Medium | Project storage versioning | Users can roll back and compare outputs | Snapshots before/after major operations | Storage growth | Not in Phase 1.5 |
| Subtitle Editor | Later | 3.0 / 3.1 | Medium | Video/subtitle export | Captions need text/timing polish | Edit Arabic/English text and timing; export SRT/VTT | RTL rendering/timing bugs | Not in Phase 1.5 |
| Export Presets | Later | 3.3 | Medium | Image/audio/subtitle/video outputs | Platform-ready outputs | YouTube 16:9, Shorts 9:16, Square 1:1, audio-only, subtitle-only | Render complexity | Not in Phase 1.5 |
| Job Queue Dashboard | Mid-term | Cross-cutting | Medium | Unified job metadata | Gives confidence during long jobs | Queue, ETA, retry, affected scene, engine/status | Fake progress risk | Not in Phase 1.5 except naming consistency |
| Safety & Rights Checklist | Near/Mid-term | Before voice/reference expansion | High | Asset metadata | Prevents unsafe voice/image reference usage | Source/license/consent captured for voices/images | Legal nuance | Not in Phase 1.5 unless passive notes only |
| Model / Engine Dashboard | Later | Ops/status track | Medium | Benchmark matrix, health endpoints | Shows engine status without direct AI Server exposure | Health, benchmark verdict, VRAM warning | Could expose internals if careless | Not in Phase 1.5 |
| Separate Image Studio | Mid-term | 2.5 | High | Image worker, safety checklist | General image/design tool separate from story scenes | Prompt-to-image, image-to-image, inpaint/outpaint later, poster/certificate/social design | Scope creep into design suite | Not in Phase 1.5 |
| Genre-Aware Story Improvement | Near/Mid-term | Text layer upgrade | Medium | Prompt architecture | Better story/narration per genre | Horror/military/documentary/warm/children/marketing profiles | Prompt drift | Not in Phase 1.5 unless copy-only |

## Research Notes

Practical patterns observed:

- Professional video workflows rely on markers/timelines to organize time-based media and review points.
- Media asset management tools treat metadata/search/review/approval as core features, not extras.
- Video approval workflows separate technical output from human approval.
- Automated media APIs use JSON edit lists/assets and asynchronous render jobs.
- Caption workflows commonly use sidecar SRT/VTT first, then optional burned-in subtitles.
- AI image consistency usually needs reference images/IP-Adapter/ControlNet/LoRA-style workflows; prompt-only is not reliable enough.
- AI voice/image reference use needs consent, licensing, and metadata records.

References:

- Adobe Premiere markers: https://helpx.adobe.com/premiere/desktop/organize-media/apply-labeling/overview-of-markers.html
- Adobe subtitles workflow: https://www.adobe.com/creativecloud/video/discover/add-subtitles-to-video.html
- Shotstack video editing API: https://shotstack.io/docs/api/
- Shotstack subtitles: https://shotstack.io/learn/generate-srt-vtt-subtitles-api/
- Shotstack burn-in captions: https://shotstack.io/learn/burn-subtitles-captions-api/
- IP-Adapter paper: https://arxiv.org/abs/2308.06721
- ComfyUI ControlNet + IPAdapter workflow: https://comfyui.org/en/image-style-transfer-controlnet-ipadapter-workflow
- Voice cloning safety / FTC: https://www.ftc.gov/policy/advocacy-research/tech-at-ftc/2023/11/preventing-harms-ai-enabled-voice-cloning

## What We Do Not Trust Without Benchmark

- Any image consistency method that has not been tested on the actual AI Server.
- Any video workflow that has not produced an MP4 on the actual hardware.
- Any TTS engine or voice that has not passed licensing/safety checks.
- Any “real-time” progress or ETA claim without worker-side measurements.

