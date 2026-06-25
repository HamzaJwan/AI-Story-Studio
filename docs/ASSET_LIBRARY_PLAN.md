# Project Asset Library Plan

Last updated: 2026-06-25

## Purpose

The Asset Library is the per-project media catalog for generated and reference assets.

This is not part of Phase 1.5.

## Asset Types

- Audio files.
- Generated images.
- Subtitle files.
- Video exports.
- Reference images.
- Character anchors.
- Style references.
- Previous outputs.
- Metadata and source/license notes.

## Why It Matters

- Generated media must be discoverable.
- Assets need preview/download links.
- Assets should link back to scenes.
- Future regenerate/retry workflows need stable asset metadata.
- Git must never contain generated media.

## Proposed Phase

Phase 2.7 — Production Studio Foundations.

## Dependencies

- Stable project storage paths.
- Backend proxy download endpoints.
- Scene/image/audio/subtitle metadata.
- Safety and rights metadata for reference assets.

## Acceptance Criteria

- User can preview supported assets.
- User can download assets.
- User can see which scene owns an asset.
- User can see source/license/consent notes for reference assets.
- Generated files remain in ignored project data paths.

## Risks

- Storage bloat.
- Orphaned files after scene deletion.
- Accidentally committing generated media.
- Exposing local filesystem paths to the browser.

## Not In Current Phase

Do not build this in Phase 1.5. Only audio-specific playback/download should be improved now.

