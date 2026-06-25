# UX Job Progress Plan

Last updated: 2026-06-25

Audio, image, and video generation should share one job-progress model so the user never feels the app froze.

## Job States

Use a simple shared vocabulary:

- `queued`
- `preparing`
- `running`
- `postprocessing`
- `done`
- `failed`
- `cancelled`

## Job Fields

Recommended fields:

- `job_id`
- `project_id`
- `kind` — `audio`, `image`, `video`
- `status`
- `current_step`
- `total_steps`
- `progress_percent`
- `elapsed_seconds`
- `eta_seconds`
- `queue_position`
- `engine`
- `worker`
- `output_files`
- `warnings`
- `error`

If exact progress is not available, show coarse truthful states instead of fake precision.

## Frontend Behavior

- Show project-level and scene-level status.
- Keep a visible activity indicator during long operations.
- Show elapsed time even when ETA is unknown.
- Keep generated outputs attached to the scene/project.
- Allow retry for failed scenes without re-running the whole project.
- Show short, human-readable errors in Arabic.
- Later: add a Job Queue Dashboard that shows all audio/image/subtitle/video/export jobs in one place.
- Later: include affected scene, engine used, current step, retry button, and warning states.

## Backend Behavior

- Backend owns job orchestration.
- Frontend polls backend first; backend talks to AI Server workers.
- Direct browser-to-AI-Server access is not allowed.
- Store job metadata in project JSON or local ignored data paths.
- Keep worker logs summarized, not dumped into the UI by default.

## Later Upgrade

Polling is enough for the next phase. Server-Sent Events or WebSocket can be considered later if polling becomes noisy or slow.

## Job Queue Dashboard — Later

The dashboard should show:

- queued
- preparing
- running
- postprocessing
- done
- failed
- elapsed time
- ETA when available
- retry failed
- affected scene
- engine/service used
- output file links
- warning if a required asset is missing

This is not part of Phase 1.5 except for using consistent status names.
