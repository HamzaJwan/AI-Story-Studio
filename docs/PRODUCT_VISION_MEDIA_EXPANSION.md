# Product Vision — Media Expansion

Last updated: 2026-06-25

AI Story Studio is moving from a text-only story workspace into a local-first media studio. The key is to expand in layers, not by mixing every engine into the main app at once.

## Product Direction

1. **Story Workspace** — create, improve, split, edit, save, and export story projects.
2. **Audio Layer** — generate narration per scene through an isolated AI Server worker.
3. **Image Layer** — generate scene images through an isolated AI Server image worker.
4. **Continuity Layer** — preserve characters, places, objects, colors, style, and story logic.
5. **Video Layer** — assemble images + narration + subtitles/captions + transitions before full AI video.
6. **Image Studio** — a separate workspace for general image generation/editing use cases.
7. **Production Studio Layer** — timeline, asset library, review board, regenerate controls, version history, and export presets.
8. **Local AI Assistant Layer** — use existing Open WebUI/Ollama/RAG/vision capabilities as a lab before any Story Studio integration.

## Image Studio Scope

The Image Studio should be separate from the story flow. Candidate use cases:

- Prompt-to-image.
- Reference-image editing.
- Marketing poster / thumbnail.
- Certificate / invitation / graphic design.
- Personal image transformation with user-owned or consent-safe references.
- Person/object into scene with clear consent and safety boundaries.

## Production Studio Scope

The long-term product should behave like a lightweight production studio:

- Timeline view across scene, narration, audio, image, subtitle, duration, and video segment.
- Asset library inside each project for generated and reference media.
- Quality review board for approval/retry/reject decisions.
- Per-scene regeneration rather than full-project reruns.
- Version history/snapshots so users do not lose work.
- Export presets for social/video/audio/story package outputs.

## Genre-Aware Writing

Story improvement should eventually support genre profiles:

- Horror/suspense: controlled pacing, dread, sensory detail.
- Military: discipline, clarity, tactical realism, mission language.
- Warm drama: emotional memory, soft narration, intimate tone.
- Cinematic: visual beats, hooks, transitions.
- Documentary: grounded explanation and factual rhythm.

The genre profile should influence narration, scene splitting, image prompts, audio tone, and later video pacing.

## Architecture Direction

- Main backend orchestrates jobs and stores project metadata.
- AI Server hosts workers: Ollama, TTS worker, image worker, future video worker.
- Frontend talks only to the main backend.
- Generated media is stored in ignored local project data paths and exported through project packages.
- Asset metadata, licenses, source notes, benchmark verdicts, and quality approvals should be stored with the project.
- Open WebUI remains a separate AI Server service until a safe integration plan exists.

## Local AI Assistant Direction

Do not build a ChatGPT/Gemini clone from scratch. The realistic path is:

- Use existing Open WebUI as the lab interface.
- Use existing Ollama as the local model runtime.
- Use RAG/Knowledge for project docs instead of fine-tuning first.
- Use web search only with citations and only when current external information is needed.
- Use vision models only after benchmark on the AI Server.
- Later, expose Story Studio project context through backend-approved tools if the lab proves useful.

## Subtitle Direction

Future video exports should support subtitles as a first-class media layer:

- Arabic subtitles generated from `narration_ar`.
- Optional English subtitles when English narration/translation exists.
- Sidecar subtitle export: `.srt` and/or `.vtt`.
- Optional burned-in subtitles in the final MP4.
- Per-scene timing first, then word/phrase-level timing if audio alignment becomes available.
- Editable subtitle text separate from narration when the user wants shorter on-screen captions.

## Next Practical Step

The next execution step remains Phase 1.5 — Audio UX Polish. After that, return to image quality approval and the image worker bridge. The production-studio features stay documented until audio/image basics are stable.
