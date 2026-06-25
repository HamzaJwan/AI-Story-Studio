# Product Vision — Media Expansion

Last updated: 2026-06-25

AI Story Studio is moving from a text-only story workspace into a local-first media studio. The key is to expand in layers, not by mixing every engine into the main app at once.

## Product Direction

1. **Story Workspace** — create, improve, split, edit, save, and export story projects.
2. **Audio Layer** — generate narration per scene through an isolated AI Server worker.
3. **Image Layer** — generate scene images through an isolated AI Server image worker.
4. **Continuity Layer** — preserve characters, places, objects, colors, style, and story logic.
5. **Video Layer** — assemble images + narration + captions + transitions before full AI video.
6. **Image Studio** — a separate workspace for general image generation/editing use cases.

## Image Studio Scope

The Image Studio should be separate from the story flow. Candidate use cases:

- Prompt-to-image.
- Reference-image editing.
- Marketing poster / thumbnail.
- Certificate / invitation / graphic design.
- Personal image transformation with user-owned or consent-safe references.
- Person/object into scene with clear consent and safety boundaries.

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

## Next Practical Step

Before adding more capabilities, Phase 2.1 should build a safe image worker bridge and status flow. Image quality and continuity should be proven before large-scale story image generation.

