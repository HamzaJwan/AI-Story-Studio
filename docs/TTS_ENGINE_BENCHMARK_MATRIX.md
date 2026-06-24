# TTS Engine Benchmark Matrix

Phase 1.0 is a benchmark matrix, not an application integration.

| Engine | Status | Where to run | Pros | Risks | Decision |
| --- | --- | --- | --- | --- | --- |
| SILMA | PASS on AI Server GPU benchmark | AI Server Docker lab | Arabic-focused, generated WAV/MP3 | heavy first bootstrap/build cost | PASS, keep isolated |
| AllTalk/XTTS | Candidate, pending service-based test | AI Server external service | Existing API/Docker service possible | voice licensing, quality/size | test as fallback service |
| Piper Arabic | not tested | App or AI Server | light/fast | lower narration quality | emergency fallback |

## Current SILMA Status

- Result: `PASS`.
- Environment: AI Server Docker lab with GPU/CUDA available.
- GPU: RTX 4060 Ti.
- Commit tested: `a616f61 fix: slim SILMA lab benchmark dependencies`.
- Output WAV generated: `deploy/ai-server/silma-lab/data/benchmarks/tts/silma/test_audio_silma.wav` (~578K).
- Output MP3 generated: `deploy/ai-server/silma-lab/data/benchmarks/tts/silma/test_audio_silma.mp3` (~95K).
- Reference used: bundled official SILMA Arabic reference audio `official_silma_ar.ref.24k.wav`.
- First generation time: `256.95s`.
- First bootstrap/build was heavy because it downloaded many PyPI/HuggingFace dependencies.
- Successful build path used direct Docker build with `--network=host`.
- Final successful path did not require `pynini`, `nemo_text_processing`, `gradio`, or `onnxruntime`.
- Decision: SILMA passed, but the bootstrap cost is heavy; keep it isolated as an AI Server Docker lab until a production worker API is designed.

## AllTalk/XTTS Status

- Status: `Candidate / Pending test`.
- Intended mode: service-based benchmark against an already running AllTalk-compatible TTS service.
- Target URL placeholder: `TTS_SERVICE_URL=http://AI_SERVER_IP:7851`.
- Do not copy AllTalk source code into this repository.
- Do not use celebrity voices or real-person voices without explicit permission.
- Use only licensed or safe test voices.

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

Keep SILMA as a passed isolated lab, then run the AllTalk service-based benchmark scaffold when a safe/licensed test voice is available.
