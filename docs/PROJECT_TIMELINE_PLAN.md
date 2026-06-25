# Project Timeline View Plan

Last updated: 2026-06-25

## Purpose

The Project Timeline View should become the heart of the production workspace. It connects every scene to its narration, audio, image, subtitle, duration, video segment, status, warnings, and review actions.

This is not part of Phase 1.5.

## Why It Matters

- Users need to see the whole story as a timed production, not a pile of files.
- Missing assets become obvious.
- Per-scene retry/review becomes natural.
- Video assembly later needs the same timeline data.

## Proposed Phase

Phase 2.7 — Production Studio Foundations.

## Dependencies

- Phase 1.5 Audio UX Polish.
- Scene image generation basics.
- Asset metadata for audio/image/subtitles.
- Unified job status naming.

## Timeline Row Fields

Each scene row should eventually show:

- scene id/title
- narration status
- audio status/player
- image status/thumbnail
- subtitle status
- duration
- video segment status
- warnings
- approve/retry/reject actions

## Acceptance Criteria

- Scenes appear in chronological order.
- Missing audio/image/subtitle/video assets are visible.
- Total project duration is visible.
- Each row links to review/regenerate actions.
- No generated file is committed to Git.

## Risks

- Too much UI too early.
- Metadata may drift from files if storage rules are weak.
- Long projects need filtering/collapse/search.

## Not In Current Phase

Do not build this in Phase 1.5. Phase 1.5 should only polish audio UX.

