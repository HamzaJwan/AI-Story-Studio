# Video Subtitles Plan

Last updated: 2026-06-25

## Purpose

Subtitles should become a first-class layer in future video exports. When the narrator speaks, the video should be able to show matching Arabic or English text on screen.

This is not part of Phase 1.5. It belongs to the future video track.

## Why It Matters

- Makes story videos easier to watch without sound.
- Helps Arabic narration feel complete and shareable.
- Supports social/video platforms that expect captions.
- Reuses data the project already has: scene narration, scene duration, generated audio metadata, and later image/video timing.

## Subtitle Sources

Initial source:

- `scene.narration_ar`
- `scene.duration_seconds`

Future optional sources:

- Edited subtitle text per scene.
- English translation/subtitle text.
- Word/phrase timing from audio alignment if available later.

## Output Formats

Phase 3.0 should start with sidecar files:

- `.srt`
- `.vtt`

Phase 3.1 can add burned-in subtitles:

- Rendered directly into the exported MP4.
- Optional, not forced.

## Timing Strategy

### Phase 3.0 — Scene-Level Timing

Use scene boundaries:

- Subtitle start = scene start time.
- Subtitle end = scene start + `duration_seconds`.
- Split long narration into readable chunks if needed.

This is good enough for the first story video/animatic.

### Later — Phrase/Word-Level Timing

If audio alignment becomes available:

- Split subtitles by phrase.
- Match text chunks to narration timing.
- Improve readability for long scenes.

## Language Strategy

- Arabic first.
- English optional if the project has English narration or translation.
- Do not auto-translate unless a future approved text pipeline exists.

## Styling Strategy

For burned-in MP4 subtitles later:

- High contrast text.
- Safe bottom area.
- RTL Arabic rendering.
- Optional style presets:
  - cinematic lower-third
  - documentary clean
  - social short-form bold

## Subtitle Editor — Future UI

Later, the user should be able to:

- Edit subtitle text per scene.
- Adjust scene-level timing.
- Split long narration into shorter readable subtitle blocks.
- Add English subtitles when translation exists.
- Preview subtitles before MP4 export.
- Choose sidecar-only or burned-in subtitles.

This belongs to Phase 3.0 / Phase 3.1, not Phase 1.5.

## Acceptance Criteria

For Phase 3.0:

- Export contains `.srt` or `.vtt`.
- Arabic text remains UTF-8 clean.
- Subtitle timing follows scene order.
- Long narration is split into readable blocks.

For Phase 3.1:

- MP4 can be exported with visible subtitles.
- Sidecar subtitles can still be exported separately.
- User can choose subtitles on/off.

## Do Not Implement Now

- Do not add video subtitles during Phase 1.5.
- Do not start MP4 assembly yet.
- Do not add image/video workers for this feature now.
- Keep this as roadmap documentation until the video track begins.
