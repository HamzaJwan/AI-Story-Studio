# Quality Review Board Plan

Last updated: 2026-06-25

## Purpose

The Quality Review Board gives Hamza or the user a structured way to approve, retry, or reject scene outputs.

Technical PASS does not mean product-quality PASS.

## Review Items

Per scene, show:

- narration text
- audio status/player
- generated image
- subtitle status
- warnings
- quality notes
- approve/retry/reject controls

## Why It Matters

- Image/audio/video generation can succeed technically but fail creatively.
- Multi-scene consistency needs human approval.
- Failed scenes should be retried individually.
- Video export should not proceed with unapproved critical assets.

## Proposed Phase

Phase 2.7 — Production Studio Foundations, before serious video export.

## Dependencies

- Asset Library.
- Project Timeline View.
- Per-scene regenerate actions.
- Stable quality status fields.

## Acceptance Criteria

- Every scene can be marked approved/retry/rejected.
- Notes can be attached to a scene or asset.
- Review status blocks video export if configured as strict.
- Retrying one scene does not rerun the whole project.

## Risks

- Review state can become too complex.
- Users may need bulk approval for simple projects.
- Need clear difference between “technical success” and “approved”.

## Not In Current Phase

Do not build this in Phase 1.5. Keep Phase 1.5 focused on audio UX.

