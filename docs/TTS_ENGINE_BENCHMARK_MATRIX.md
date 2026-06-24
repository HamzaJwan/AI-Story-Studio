# TTS Engine Benchmark Matrix

Phase 1.0 is a benchmark matrix, not an application integration.

Every row below must follow the Benchmark Gate fields defined in `docs/BENCHMARK_PROTOCOL.md` (engine, version, hardware, command, output sample, cold/warm time, VRAM, quality notes, limitations, verdict). No engine here is integrated into the product (`backend/` or `frontend/`) regardless of verdict — integration is a separate, explicitly-approved phase (Phase 1.1 TTS Worker API), and only after a row reaches `PASS`.

| Engine | Verdict (Benchmark Gate) | Where to run | Pros | Risks | Decision |
| --- | --- | --- | --- | --- | --- |
| SILMA | `PASS` (Phase 1.0 isolated lab script) / `BLOCKED` (Phase 1.2 worker, 2026-06-24) | AI Server Docker lab / `deploy/ai-server/tts-worker/` | Arabic-focused, generated WAV/MP3 | heavy first bootstrap/build cost; ~2GB model download stalled on this run (network, not code) | keep code in place behind `ENGINE=silma`, retry when network is healthier |
| Piper (ar_JO-kareem-medium) | `PASS` (Phase 1.2 worker, 2026-06-24) | `deploy/ai-server/tts-worker/` (default engine) | Lightweight (~60MB voice), fast warm runs (~4s), GPL-3.0 library + MIT-tagged voice repo | Lower expressiveness than SILMA; CPU-only in current config | **Default engine for Phase 1.2**, used for Phase 1.3 |
| AllTalk/XTTS | `CANDIDATE` — pending real service-based test | AI Server external service | Existing API/Docker service possible | voice licensing, quality/size | must run real Benchmark Gate before any further status change |

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

## Phase 1.2 Worker Attempt — 2026-06-24

### SILMA via `deploy/ai-server/tts-worker/` (`ENGINE=silma`) — `BLOCKED`

- Container built and ran correctly; GPU confirmed visible inside the container (`device: cuda`, `nvidia-smi` working, RTX 4060 Ti / 8188 MiB).
- The ~2GB SILMA model checkpoint download from HuggingFace's Xet CDN (`us.aws.cdn.hf.co`) stalled completely twice (identical byte count over multiple 15-30s windows, TCP retransmissions confirmed via `/proc/net/tcp`) — diagnosed as a real network/CDN throughput problem on this AI Server tonight, not a SILMA code or model defect. A direct `curl` range request to the exact same URL succeeded at 200-530 KB/s in isolation, confirming the path is *capable* of working, just unreliable for a single long-lived download.
- Decision: keep the SILMA code path intact behind `ENGINE=silma` for a future retry when network conditions are better verified; do not block the rest of Phase 1.2 on it.

### Piper (`ar_JO-kareem-medium`) via `deploy/ai-server/tts-worker/` (`ENGINE=piper`, default) — `PASS`

- Engine: `piper-tts==1.4.2` (GPL-3.0-or-later), voice `ar_JO-kareem-medium` from `rhasspy/piper-voices` (HF repo tagged `license:mit`; voice card: dataset from `github.com/AliMokhammad/arabicttstrain`, finetuned from the English `lessac` voice). Not Hamza's voice, not a celebrity, not a real-person clone.
- Hardware: AI Server, RTX 4060 Ti (CPU inference in this config — `use_cuda=False`, fast enough for short narration; GPU available if needed later).
- Command: `POST http://localhost:8851/api/tts/jobs {"text": "...", "format": "wav"}`, polled via `GET .../jobs/{id}`.
- Two real runs:
  1. Short text (`"هذا اختبار صوت عربي قصير لمشهد واحد."`) — cold run (included ~63MB voice download under degraded network): completed in ~6 min; output `audio.wav`, 221,740 bytes, mono 22,050 Hz, 5.03s, verified non-silent (max amplitude 32767, RMS ≈ 4051, 98.6% non-zero samples).
  2. Longer text with punctuation and a number (`"...يقارب 100 نجمة، وقال بصوت هادئ: لن أنسى هذا اليوم أبداً!"`) — warm run (voice cached): completed in **~3.8s**; output 756,268 bytes, 17.15s duration, no crash on digits/punctuation.
- Both files downloaded and verified via `GET .../jobs/{id}/download/wav` (HTTP 200, correct WAV headers, real waveform data).
- Known limitations: GPL-3.0 library license (network-only HTTP integration, not statically linked, so this does not affect the main app's license); quality is lower than SILMA's expressiveness; CPU-only in current config.
- Verdict: `PASS`. This is the default engine for Phase 1.2 and what Phase 1.3 connects to.

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
