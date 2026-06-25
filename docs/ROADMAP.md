# AI Story Studio — Product Roadmap

Last updated: 2026-06-25

Owner: Hamza

Current recommendation: **Hamza's manual end-to-end review of the Studio MVP** (Milestone G QA pass). After sign-off, the next engineering track should be **Production Studio Foundations**: job queue/progress, timeline view, asset library, quality review board, then better ffmpeg video assembly. The full future backlog is now tracked in `docs/REMAINING_FEATURES_BACKLOG.md`.

**2026-06-25 update — Production MVP hardening pass complete.** A full manual-QA hardening round fixed two real validation bugs (scene duration min mismatch, empty-title save error), added per-step completion indicators and an unsaved-changes indicator to the workflow UI, added spinners + clearer text to every long-running action, and made the export step list every downloadable asset with explicit available/missing state. No new features, no architecture change. See `docs/DECISION_LOG.md` for the full entry.

---

## 1. Current Verified State

| Area | State |
|---|---|
| Core story app | PASS — project workspace, scene editing, package export, RTL Arabic UX |
| Ollama story pipeline | PASS — improve story, split scenes, scenes.json |
| Audio pipeline | PASS — Piper worker generated real WAV, app can request audio, export.zip can include audio |
| Audio UX | PASS — voice/language selectors, per-scene + full-story playback, all backend-proxied, no ZIP digging required |
| SILMA | PASS as isolated AI Server lab, but heavy bootstrap cost |
| Image pipeline | PASS — ComfyUI + SDXL bridged through the backend, persisted per-scene generate/regenerate/generate-all, quality `CANDIDATE` (not final-approved) |
| Continuity foundation | PASS — project-level style/character/location/object bibles + 6 style presets injected into every prompt; verified fix for a real style-drift bug found during testing |
| Video assembly | PASS — ffmpeg static-image + audio MP4, verified frame-by-frame with ffprobe |
| Subtitle export | PASS — .srt/.vtt generated from narration_ar + duration_seconds, timing matches the rendered video exactly |
| End-to-end pipeline | PASS — verified on one fresh project from creation through export.zip in a single run (see `docs/DECISION_LOG.md` Milestone G entry) |
| Current product gate | **Hamza's manual hands-on QA pass** (see `docs/MANUAL_QA_CHECKLIST.md`) — product-quality sign-off, not a technical blocker |

The Studio MVP pipeline (story → scenes → audio → scene images → continuity → video → subtitles → export) is technically complete and verified with real data, including a real fix for a real continuity bug found mid-build. It does **not** yet have face-locked character consistency, AI video motion, advanced transitions, or burned-in subtitle styling — those are explicitly deferred to later phases (3.1+, 3.2+).

Manual ComfyUI lessons are documented in `docs/COMFYUI_MANUAL_TEST_NOTES.md`. The key product lesson is that SDXL Base is viable for MVP images, but prompt-only continuity can still drift across gender/identity — Phase 2.3 addressed this with bibles/negative prompts/style presets; pixel-level/face-locked continuity remains a later tier.

---

## 2. Non-Negotiable Product Rules

- The App/Production server must not run heavy GPU workloads.
- Ollama, TTS, ComfyUI, and future WanGP stay on the AI Server as separate LAN services.
- The frontend must not call AI Server services directly; the backend is the orchestrator/proxy.
- No hardcoded real IPs, credentials, or secrets in code or docs.
- No `.env`, generated media, model caches, `node_modules`, or `dist` in Git.
- Every media engine needs a benchmark gate before product integration.
- Long-running media work must be job-based with visible status/progress.
- Image quality is `CANDIDATE` (Hamza explicitly authorized MVP-stage proceeding with this candidate quality for the Studio MVP Autopilot round); it is not yet a final, signed-off product-quality approval.

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
| 2.0 | Image Benchmark Lab | TECHNICAL PASS | ComfyUI + SDXL PNG generated; quality `CANDIDATE`, MVP proceeding |
| 2.1 | Image Worker Bridge | PASS | Backend-proxied job bridge to ComfyUI; real images verified for real scenes |
| 2.2 | Story Scene Images MVP | PASS | Persisted generate/regenerate/generate-all, images in export.zip; real style-drift gap found |
| 2.3 | Continuity Foundation MVP | PASS | Project bibles + style presets injected into every prompt; style-drift bug fixed and visually verified |
| 3.0 | Video Assembly MVP | PASS | ffmpeg static-image + audio MP4 assembly; real render verified frame-by-frame with ffprobe |
| 3.0/3.1 | Subtitle Export MVP | PASS | .srt/.vtt generated from narration_ar + duration_seconds; timing matches the rendered video exactly |

---

## 4. Required Before the Next Phase (Studio MVP is done; what's left is human review)

| Item | Why | Owner |
|---|---|---|
| Hamza's hands-on Studio MVP QA pass | Every step above is engineer-verified with real data, but product feel/quality is Hamza's call, not the executor's | Hamza |
| Decide whether image/continuity quality is acceptable for real use | Quality is `CANDIDATE`; continuity is prompt-only (Tier 1) — good enough for MVP testing, not yet a final guarantee | Hamza |
| Pick the next roadmap track (Phase 2.7 Production Studio Foundations vs. Phase 3.1 video polish vs. Phase 4.x assistant lab) | All three are now unblocked; sequencing is a product priority call | Hamza |

Recommended default if Hamza wants Autopilot after QA:

1. Real Job Queue / Background Workers.
2. Project Timeline View.
3. Project Asset Library.
4. Quality Review Board.
5. Ken Burns / Better Video Assembly.

These are future features, not part of the current Production MVP. They improve the already-working pipeline without adding new model risk.

~~Sync visible UI phase/status text~~ — done, hero now shows "Phase 3.1 — استوديو متكامل: صوت، صور، فيديو، ترجمة".
~~Confirm image worker security boundary~~ — done and re-verified every milestone (grepped every response for the AI Server's address/path).
~~Confirm VRAM budget~~ — unchanged from Phase 2.0's `--lowvram` + 768×768 mitigation; no new pressure introduced.
~~Define image/video/subtitle storage shape~~ — done: `data/projects/{id}/{images,video}/`, sidecar `metadata.json` for video, all Git-ignored.

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

### Phase 2.4 — Image Style Presets — ✅ DONE (merged into Phase 2.3)

Implemented as part of Phase 2.3's continuity work rather than as a separate phase, since style presets and continuity bibles are injected into the same prompt-assembly step (`build_scene_image_prompt()`). Six presets shipped: `cinematic_realistic`, `warm_storybook`, `anime_cartoon`, `military_documentary`, `horror_suspense`, `marketing_poster` (concept art was dropped as redundant with cinematic_realistic for MVP scope; add later if a real need shows up). Exposed via `GET /api/images/style-presets` so the frontend has one source of truth.

Exit criteria — verified:
- Style choice affects prompts predictably. ✅ (`image_prompt_used` shows the exact assembled prompt)
- Same story can be rendered in at least two styles without breaking scene structure. ✅ (preset is just a prefix string; scene structure is untouched)

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

### Phase 4.0 — Local AI Assistant Lab Research

Goal: evaluate a local ChatGPT/Gemini-like assistant path by using existing AI Server services instead of building a chat system from scratch.

Scope:
- Review existing Open WebUI capabilities.
- Review current Ollama models.
- Define project-specific assistant use cases.
- Test whether Open WebUI is sufficient as the assistant UI.
- No integration inside AI Story Studio yet.

Exit criteria:
- Clear recommendation: use Open WebUI as-is, extend via Open WebUI tools/pipelines, or build a small Story Studio bridge later.
- Candidate models and RAG settings identified for benchmark.
- No changes to production app architecture.

### Phase 4.1 — Model Benchmark for Chat

Goal: choose practical default models for local chat on the AI Server.

Scope:
- Arabic chat model benchmark.
- English chat model benchmark.
- Coding/reasoning benchmark.
- Response speed and context length checks.
- Compare only models actually available or intentionally pulled for benchmark.

Exit criteria:
- Default chat model candidate selected.
- Limits documented for Arabic, English, reasoning, and long-context tasks.

### Phase 4.2 — Knowledge / RAG Setup

Goal: reduce hallucination by grounding answers in project docs instead of fine-tuning first.

Scope:
- Upload project docs, roadmap, API contracts, prompts, and selected project files into Open WebUI Knowledge/RAG.
- Test source-bound answers and citations.
- Tune chunking/context settings.
- Evaluate whether answers say “I do not know” when evidence is missing.

Exit criteria:
- Project-doc Q&A works with citations.
- Hallucination test set passes an agreed threshold.
- Fine-tuning remains deferred unless RAG + prompts + model selection prove insufficient.

### Phase 4.3 — Web Search

Goal: evaluate web search for current information, not internal project truth.

Scope:
- Test Open WebUI web search using a safe provider.
- Require citations/sources.
- Compare web results against known facts.
- Document provider choice and limitations.

Exit criteria:
- Web search can return useful sourced answers.
- Search failures/latency are understood.
- Assistant does not confuse web results with internal project documents.

### Phase 4.4 — Vision Chat

Goal: evaluate local image-understanding models for screenshots, UI review, and future scene analysis.

Scope:
- Benchmark candidates such as `qwen2.5vl`, `llama3.2-vision`, or `llava` if suitable for hardware.
- Upload screenshots and ask UI/quality questions.
- Test Arabic/English descriptions.
- Do not rely on vision output without human review.

Exit criteria:
- A practical vision model candidate is selected or marked blocked.
- Accuracy and speed are documented.

### Phase 4.5 — Story Studio Assistant Tools

Goal: later connect assistant workflows to AI Story Studio safely.

Scope:
- Assistant can read current story/project context through backend-approved data.
- Assistant can suggest story improvements, scene fixes, continuity notes, image prompts, and bibles.
- Assistant cannot mutate project data without explicit user approval.
- Any integration uses backend boundaries, not direct browser-to-AI-Server calls.

Exit criteria:
- Clear tool boundary.
- Human approval required for edits.
- No mixing Open WebUI storage with Story Studio project storage without a plan.

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

### Local AI Assistant Lab

The local assistant path is documented in `docs/LOCAL_AI_ASSISTANT_LAB_PLAN.md`.

This is a Phase 4.x lab track. It should use the existing Open WebUI + Ollama services first, not a new custom chat app.

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

**Recommended next action: Hamza final manual QA only.**

If Hamza approves the Production MVP, the next Autopilot execution track should be **Production Studio Foundations**, in this order:

1. Real Job Queue / Background Workers.
2. Project Timeline View.
3. Project Asset Library.
4. Quality Review Board.
5. Ken Burns / Better Video Assembly.

Do not start AI motion, local assistant integration, new TTS engines, public deployment, DB/Auth, or advanced continuity until the foundation track is stable and explicitly approved.
