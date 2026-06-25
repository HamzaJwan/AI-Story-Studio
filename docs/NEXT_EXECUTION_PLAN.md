# Next Execution Plan

Last updated: 2026-06-25

## Current Recommendation

**Do not add new product features before Hamza final manual QA.**

The Production MVP is accepted technically. The next engineering track after sign-off should be **Production Studio Foundations**, not another AI model integration.

Recommended first track after QA:

1. Real Job Queue / Background Workers.
2. Project Timeline View.
3. Project Asset Library.
4. Quality Review Board.
5. Ken Burns / Better Video Assembly.

See `docs/REMAINING_FEATURES_BACKLOG.md` for the full future backlog.

## Why This Order

- It improves the existing working pipeline instead of opening a new model risk.
- It follows proven production patterns: jobs for long-running tasks, timeline/asset-library/review-board for media workflows, and ffmpeg-based motion polish before heavy AI video.
- It avoids adding DB/Auth/public deployment until the local studio experience is stable.

## Do Not Do Next

- Do not start AI motion / WanGP / AnimateDiff / SVD.
- Do not add a custom local chat assistant before evaluating Open WebUI/Ollama RAG as a lab.
- Do not add new TTS engines before a benchmark/safety pass.
- Do not expose AI Server URLs to the browser.
- Do not touch `.env` or commit generated media.
- Do not add DB/Auth/Redis/Celery without an approved architecture step.

## AUTOPILOT_NEXT_EXECUTION_PROMPT

You are now Lead Executor inside AI Story Studio.

Task: implement the **Post-MVP Production Studio Foundations** track only, after confirming the current Production MVP remains clean.

This is not a new AI-model phase. Do not add WanGP, AnimateDiff, SVD, new TTS engines, public deployment, DB/Auth, or a custom chat assistant.

### Start First

Run:

```powershell
git fetch origin
git checkout main
git pull --ff-only origin main
git status --short --branch
git log --oneline -12
python scripts/check_utf8.py
python scripts/final_acceptance_check.py
```

If Git conflicts, generated media in Git, or acceptance check failures appear, stop and produce a handoff report before implementing.

### Milestone A — Job Queue / Progress Foundation

Goal: stop long image/video operations from feeling frozen.

Implement only a lightweight local job system unless a larger architecture is explicitly approved.

Scope:

- Define a common job model: `queued`, `running`, `done`, `failed`, `cancelled`.
- Add backend job metadata storage under ignored project data.
- Convert only the safest long-running operation first, preferably image generate-all or video render.
- Add polling endpoint and clear frontend status.
- Do not add Redis/Celery/DB unless explicitly approved.

Acceptance:

- Existing synchronous endpoints still work or are clearly backward compatible.
- New job endpoint returns `job_id`.
- UI can poll and show progress text without fake ETA.
- Failed jobs expose a safe error message.
- No generated media or job files are committed.

Commit:

```text
feat: add lightweight studio job progress foundation
```

### Milestone B — Project Timeline View

Goal: make every scene's production state visible in one view.

Scope:

- Add a Timeline step or section.
- Show each scene with: title, duration, narration, audio status, image status, subtitle status, video inclusion, approval status placeholder.
- Link to existing edit/audio/image/video/export actions.
- No new generation engine.

Acceptance:

- Timeline works for projects with 0 scenes, partial assets, and full assets.
- Scene order and duration are readable.
- Missing assets are explicit.

Commit:

```text
feat: add project timeline view
```

### Milestone C — Asset Library

Goal: make project outputs discoverable without opening ZIP.

Scope:

- Add project asset library grouped by: story/scenes, audio, images, video, subtitles, exports.
- Use existing backend-relative download endpoints.
- Do not expose filesystem paths or AI Server URLs.

Acceptance:

- Existing asset-rich project shows all available assets.
- Empty/partial projects show clear missing states.
- Downloads work through backend.

Commit:

```text
feat: add project asset library
```

### Milestone D — Quality Review Board

Goal: let Hamza approve/retry/reject scene outputs before final export.

Scope:

- Store lightweight review state in project JSON.
- Per-scene status: `pending`, `approved`, `needs_retry`.
- Notes field.
- No AI review automation yet.

Acceptance:

- Review state persists after save/load.
- Export still works.
- No generated assets are deleted by review state changes.

Commit:

```text
feat: add scene quality review board
```

### Milestone E — Better Video Assembly

Goal: improve current ffmpeg video without heavy AI motion.

Scope:

- Add optional Ken Burns pan/zoom and fade/crossfade settings.
- Keep default safe/simple.
- Preserve current MP4 export.
- Do not start AI video labs.

Acceptance:

- Video still renders with existing static mode.
- Optional motion mode creates a playable MP4.
- Subtitles/sidecar files still export.

Commit:

```text
feat: add basic video assembly polish
```

### Required Validation After Every Milestone

Run:

```powershell
python scripts/check_utf8.py
python -m compileall backend/app
docker compose config
docker compose exec -T frontend npm run build
python scripts/smoke_phase0_workspace.py
python scripts/final_acceptance_check.py
git status --short
```

Before each commit, verify:

- No `.env`.
- No generated `png/wav/mp3/mp4/zip`.
- No model files (`safetensors`, `ckpt`, `gguf`).
- No AI Server URL in frontend source or build output.

### Final Report Required

Return:

1. Milestones completed.
2. Commits pushed.
3. Validation results.
4. Media/Git safety check.
5. Known limitations.
6. Whether the app is ready for Hamza review.
