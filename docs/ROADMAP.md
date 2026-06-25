# AI Story Studio — Product Roadmap

Last updated: 2026-06-25

Owner: Hamza

Current recommendation: **Hamza's image quality sign-off** (unblocks Phase 2.1), or a Manual QA Pack / `App.tsx` cleanup pass. Phase 1.5 is done.

---

## 1. Current Verified State

| Area | State |
|---|---|
| Core story app | PASS — project workspace, scene editing, package export, RTL Arabic UX |
| Ollama story pipeline | PASS — improve story, split scenes, scenes.json |
| Audio pipeline | PASS — Piper worker generated real WAV, app can request audio, export.zip can include audio |
| Audio UX | PASS — voice/language selectors, per-scene + full-story playback, all backend-proxied, no ZIP digging required |
| SILMA | PASS as isolated AI Server lab, but heavy bootstrap cost |
| Image pipeline | TECHNICAL PASS — ComfyUI + SDXL generated a real PNG on the AI Server |
| Product image quality | PENDING — Hamza must approve visual quality before Phase 2.1 |
| Current product gate | **Hamza's image quality decision is the only thing blocking Phase 2.1** |

Phase 2.0 proves image generation can run on the AI Server. It does **not** yet prove product-ready quality, character continuity, long-story consistency, or acceptable UX for multi-step jobs.

---

## 2. Non-Negotiable Product Rules

- The App/Production server must not run heavy GPU workloads.
- Ollama, TTS, ComfyUI, and future WanGP stay on the AI Server as separate LAN services.
- The frontend must not call AI Server services directly; the backend is the orchestrator/proxy.
- No hardcoded real IPs, credentials, or secrets in code or docs.
- No `.env`, generated media, model caches, `node_modules`, or `dist` in Git.
- Every media engine needs a benchmark gate before product integration.
- Long-running media work must be job-based with visible status/progress.
- Phase 2.1 must not start until Hamza approves the generated image quality from Phase 2.0.

---

## 3. Completed Phases

| Phase | Name | Status | Notes |
|---|---|---|---|
| 0.0 | Foundation | DONE | Git, Docker, UTF-8, docs, safe env examples |
| 0.1 | Ollama Story Workspace | PASS | Improve story, split scenes, download scenes.json |
| 0.2 | Project Workspace | PASS | Local JSON project CRUD and editable scenes |
| 0.3 | Scene Editing UX Polish | PASS | Scene cards, reorder/copy/add/delete, validation |
| 0.4 | Story Package Export | PASS | Project ZIP export |
| 0.5 | Hardware-Aware Benchmark Foundation | PASS | Hardware profile and benchmark gate |
| 1.0 | SILMA Benchmark | PASS as lab | WAV/MP3 generated on GPU; heavy first bootstrap |
| 1.1 | Audio Bridge MVP | PASS | Backend/frontend bridge to external TTS worker |
| 1.2 | TTS Worker Lab API | PASS with Piper | SILMA blocked in worker by network; Piper passed |
| 1.3 | Connect App to TTS Worker | PASS | Real scene audio through backend proxy |
| 1.4 | Project Audio Export | PASS | Per-scene WAV and `final_story.wav` in ZIP |
| 1.5 | Audio UX Polish | PASS | Voice/language selectors, per-scene + full-story browser playback, backend-proxied |
| 2.0 | Image Benchmark Lab | TECHNICAL PASS | ComfyUI + SDXL PNG generated; quality sign-off pending |

---

## 4. Required Product Fixes Before Phase 2.1

| Fix | Why | Owner |
|---|---|---|
| Hamza quality sign-off on the generated SDXL image | Benchmark output must be acceptable, not just technically valid | Hamza |
| ~~Sync visible UI phase/status text~~ | Done in Phase 1.5 — hero now shows "Phase 1.5 — استوديو الصوت" | Executor |
| Confirm image worker security boundary | Browser must never call ComfyUI directly | Executor |
| Confirm VRAM budget with current AI Server services | RTX 4060 Ti 8GB had a tight SDXL margin; avoid running competing heavy services together | Executor |
| Define image output storage shape | Avoid ad-hoc image files before product integration | Executor |

Add one more product sequencing rule: Phase 1.5 should happen first because the audio backend already works and Hamza's manual test shows the current UX still forces users toward ZIP downloads instead of clear in-browser playback.

---

## 5. Proposed Updated Roadmap

### Phase 1.5 — Audio UX Polish — ✅ PASS

Goal: make the already-working TTS path usable as a real product feature before expanding into images.

Implemented:
- Voice selector and language selector (`GET /api/tts/voices` — static honest catalog, no invented options).
- Graceful single-option behavior — Piper Arabic shown selected, language locked to Arabic.
- Browser audio player for the latest single-scene job (unchanged from Phase 1.1/1.3, kept ephemeral).
- Per-scene play/download for saved scene audio (`GET /api/projects/{id}/audio`, `.../audio/{scene_id}`).
- Full project / `final_story.wav` play/download (`.../audio/final_story.wav`, computed on demand).
- Clearer Arabic job/health status copy.
- Backend proxy only — verified by grepping every response for the AI Server's address/port and internal paths; found and fixed a real leak in the pre-existing job endpoints (`files[].path`).
- No new TTS engine, no image/video work.

Exit criteria — all verified with real requests on a real 6-scene project:
- User can generate and listen to one scene inside the browser. ✅
- User can generate all scene audio (`6/6`) and listen/download per-scene audio without opening the ZIP manually. ✅
- User can play/download the full project audio (`final_story.wav`, 53.63s, verified valid). ✅
- Voice/language controls do not break when only Piper Arabic is available. ✅
- `export.zip`, project workspace, and existing TTS endpoints still work (11-file ZIP, zero-scene project still `200`). ✅

### Phase 2.1 — Image Worker Bridge

Goal: connect the app backend to an isolated AI Server image service without exposing ComfyUI to the browser.

Scope:
- Backend image client using env-based service URL.
- Health endpoint/status endpoint only.
- Optional single test job endpoint behind clear config.
- No image UI beyond a safe status surface unless approved.

Exit criteria:
- Backend can check image worker health.
- A single controlled image job can be submitted and polled.
- Generated files are stored outside Git and referenced in project metadata.
- No direct frontend-to-ComfyUI traffic.

### Phase 2.2 — Story Image Generation MVP

Goal: generate one image per selected scene and attach outputs to the project.

Scope:
- Generate for one scene first.
- Then generate all scenes sequentially.
- Save image metadata: prompt, engine, seed if used, dimensions, elapsed time, file path.
- Include images in project export ZIP.

Exit criteria:
- One scene image passes visual review.
- Multi-scene generation works without OOM.
- Failed scenes are recorded without corrupting the project.

### Phase 2.3 — Continuity Foundation

Goal: stop “same story, different world” problems before scaling image generation.

Scope:
- Story bible: visual style, era, mood, camera language.
- Character bible: fixed age, face, clothing, traits, forbidden changes.
- Location bible: persistent colors/objects/layout, e.g. white door stays white.
- Object bible: important props and symbols.
- Anchor prompts and optional reference images.

Exit criteria:
- Repeated character/location/object references remain stable across at least 6 scenes.
- User can review and edit continuity anchors before generation.

### Phase 2.4 — Image Style Presets

Goal: make image generation intentional rather than random prompt tweaking.

Initial presets:
- Cinematic realistic
- Warm storybook
- Anime/cartoon
- Military documentary
- Horror/suspense
- Concept art
- Marketing/poster style

Exit criteria:
- Style choice affects prompts predictably.
- Same story can be rendered in at least two styles without breaking scene structure.

### Phase 2.5 — Separate Image Studio

Goal: add a separate creative workspace, not mixed into the story flow.

Use cases:
- Prompt-to-image.
- Reference-image edit.
- Poster/marketing image.
- Certificate/design image.
- Personal safe image transformation.
- “Put this person/object into a scene” only with consent-safe references.

Exit criteria:
- Separate navigation and project outputs.
- No confusion between story scene images and standalone designs.

### Phase 2.6 — Long Story Image Pipeline

Goal: support stories longer than 10 scenes without losing continuity or freezing the UI.

Scope:
- Batching: 3–6 scenes per batch.
- Queue/job status.
- Anchor refresh between batches.
- Partial retry for failed scenes.
- Per-batch quality checkpoint.

Exit criteria:
- A 12+ scene story can run in batches.
- User sees progress, ETA, and failed-scene recovery.

### Phase 2.7 — Production Studio Foundations

Goal: introduce the product structures that turn generated media into a manageable studio workflow.

Scope:
- Project Timeline View: scene → narration → audio → image → subtitle → video segment.
- Project Asset Library: audio, generated images, subtitles, exports, reference images, anchors, style references, metadata.
- Quality Review Board: approve/retry/reject per scene with notes and warnings.
- Regenerate per scene: retry audio/image/subtitles/prompt without regenerating the whole project.

Exit criteria:
- Every scene shows asset status and missing items.
- Generated assets are previewable/downloadable from the project, not hidden in folders.
- Hamza can approve or reject scene outputs before video assembly.
- Failed scene outputs can be retried without restarting the full project.

### Phase 3.0 — Video Foundation

Goal: build a reliable video-like export before AI video.

Scope:
- Combine existing scene images + narration audio.
- Simple transitions, subtitles/captions, timing from scene duration.
- Generate subtitle sidecar files from scene narration: `.srt` and/or `.vtt`.
- Support Arabic subtitles first, with optional English subtitles when translation exists.
- Keep subtitles editable before final video export.
- Export as a basic story video/animatic when feasible.

Exit criteria:
- No image-to-video model required.
- Project can export a coherent visual/audio timeline.
- Export includes a readable subtitle file aligned at least per scene.

### Phase 3.1 — Story Video Assembly

Goal: improve the generated timeline into a shareable video package.

Scope:
- Better transitions.
- Scene title cards.
- Intro/outro.
- Audio normalization if needed.
- Burn-in subtitles into the MP4 as an option.
- Export separate subtitle files next to the MP4 for platforms that support captions.
- Subtitle styling presets: readable Arabic, cinematic lower-third, social short-form.
- Keep narration text and subtitle text editable independently when needed.

Exit criteria:
- Final MP4 can be exported with subtitles visible.
- A sidecar `.srt` or `.vtt` file can be exported with the same timing.
- Arabic text renders correctly without mojibake or broken RTL direction.

### Phase 3.2 — Image-to-Video Motion Lab

Goal: benchmark WanGP/Wan-style motion generation as an isolated AI Server lab.

Scope:
- No product integration before benchmark PASS.
- Test one image-to-video clip first.
- Record VRAM, time, quality, and failure modes.

### Phase 3.3 — Export Presets

Goal: export projects in practical formats for different platforms and workflows.

Scope:
- YouTube 16:9.
- TikTok/Reels/Shorts 9:16.
- Square 1:1.
- Audio-only export.
- Subtitles-only export.
- Story package export.
- Image set export.
- Video package export.

Exit criteria:
- User can choose an export preset before rendering.
- Preset output dimensions and included assets are explicit.
- Failed exports do not corrupt project data.

---

## 6. Cross-Cutting Tracks

### Genre-Aware Story/Narration

The story improvement prompt should become genre-aware:
- Horror: suspense, slow reveal, sensory dread.
- Military: precision, tactical language, disciplined pacing.
- Warm/emotional: intimate narrator, soft transitions.
- Documentary: grounded narration and factual cadence.
- Cinematic: scene hooks, visual beats, strong transitions.

This should remain in the text/story layer first, before driving audio/image/video prompts.

### Unified Job Progress UX

Audio, image, and video jobs should share one status pattern:
- queued
- preparing
- running
- postprocessing
- done
- failed

The UI should show progress, elapsed time, ETA when available, current step, and recoverable errors. Do not fake exact progress if the worker only exposes coarse status.

### Media Storage

Generated media should live under ignored project data paths and be referenced by project metadata. Git must only contain code, docs, and safe scaffold files.

### Studio Backlog

Advanced production-studio features are documented in `docs/ADVANCED_FEATURE_BACKLOG.md`. The top strategic features are:

1. Project Timeline View.
2. Project Asset Library.
3. Quality Review Board.

These are not part of Phase 1.5. They become important after audio UX polish and the first image/story media flows are stable.

---

## 7. Critical Risks Before Phase 2.1

- **Image quality risk:** SDXL technical success may still be visually below Hamza’s desired product quality.
- **Continuity risk:** prompt-only generation will not reliably keep the same character/location/object across scenes.
- **VRAM risk:** RTX 4060 Ti 8GB is workable but tight for SDXL; multiple heavy services can cause OOM.
- **UX risk:** long jobs without progress/status will feel broken.
- **Security risk:** direct browser access to AI Server services would expose internal tools.
- **Scope risk:** Image Studio, story images, and video are related but should not be implemented as one giant phase.

---

## 8. Recommendation

**Recommended next execution phase: Phase 1.5 — Audio UX Polish.**

Why:
1. Audio generation already works end to end, so UX polish gives immediate product value.
2. Hamza's current screenshots show the user still has to inspect ZIP files to confirm generated audio.
3. The browser already has a single-job audio player, but saved project audio and full story audio are not surfaced clearly.
4. Phase 2.1 still depends on image quality sign-off and continuity planning.

Do not start Phase 2.1 until:
- Audio UX is acceptable.
- Hamza approves image benchmark quality.
- The stale visible phase label/status mismatch is fixed.
- The worker bridge plan confirms backend-only access to AI Server services.
- VRAM and service-concurrency assumptions are documented.
