# TTS Engine Benchmark Matrix

Phase 1.0 is a benchmark matrix, not an application integration.

| Engine | Status | Where to run | Pros | Risks | Decision |
| --- | --- | --- | --- | --- | --- |
| SILMA | pending AI Server Docker benchmark | AI Server | Arabic-focused | heavy dependencies/reference voice | test first |
| XTTS/AllTalk | not tested | AI Server | API/Docker possible | quality/size | fallback |
| Piper Arabic | not tested | App or AI Server | light/fast | lower narration quality | emergency fallback |

## Current SILMA Status

- Windows host benchmark is not the target environment.
- Docker Desktop can be useful for quick probing, but final GPU benchmark should run on the AI Server.
- SILMA requires a permitted `REF_AUDIO` and matching `REF_TEXT` unless an official sample is bundled with the package.
- If no official sample is available, the result is `NEEDS_REFERENCE`.

## Reference Voice Rule

- Do not use Hamza's voice.
- Do not download a random voice from the internet.
- Do not use a famous person, presenter, or reciter voice.
- Do not guess reference text for a sample.
- Use only a bundled official SILMA sample with clear text, or a licensed internal reference voice.

## Later Project Integration

Do not implement this now.

Future integration should use a separate worker service:

- Backend env: `TTS_SERVICE_URL`.
- Backend sends scenes or narration segments to `tts-worker`.
- `tts-worker` returns `job_id`, `status`, and generated file metadata.
- Frontend shows an audio player after job completion.

## Next Recommended Step

Run `deploy/ai-server/silma-lab/` on the AI Server after confirming Docker, Docker Compose, NVIDIA driver, and Docker GPU runtime are working.
