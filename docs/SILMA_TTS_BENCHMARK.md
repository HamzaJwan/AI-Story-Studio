# SILMA TTS Benchmark

## الهدف

اختبار مستقل لإثبات أن SILMA TTS يستطيع توليد صوت عربي قصير قبل دمجه في التطبيق.

## طريقة التشغيل

```powershell
python -m venv .venv-silma
.venv-silma\Scripts\python -m pip install --upgrade pip
.venv-silma\Scripts\python -m pip install silma-tts soundfile
.venv-silma\Scripts\python tools\tts\silma_benchmark.py
```

## مكان المخرجات

```text
data/benchmarks/tts/silma/test_audio_silma.wav
data/benchmarks/tts/silma/test_audio_silma.mp3
```

إذا لم يتوفر `ffmpeg`، يكفي وجود WAV في Phase 1.0.

## Reference Audio

لا تستخدم صوت شخص حقيقي بدون إذن واضح. إذا احتاج SILMA مرجعاً صوتياً، ضع ملفاً مسموحاً باسم:

```text
data/benchmarks/tts/silma/reference_voice.wav
```

أو مرر المسار عبر `REF_AUDIO`.

## نتائج التجربة

- Local Windows venv was attempted with Python 3.13.
- `silma-tts` requires `numpy<=1.26.4`; on Python 3.13 this attempted a source build and stalled.
- Docker benchmark with Python 3.11 was attempted.
- Docker install progressed, but `silma-tts` pulled a very large ML dependency set including `torch`, `torchaudio`, `torchvision`, and `onnxruntime-gpu`.
- The install was stopped under the benchmark Stop Conditions before audio generation.
- No WAV or MP3 was generated in this run.

## المشاكل

- Windows Python 3.13 is not a good target for this benchmark.
- SILMA install footprint is large enough that it should run on the Ubuntu AI server or a prepared Docker image.
- `ffmpeg` was not available on the Windows host, so MP3 conversion was not tested.
- No SSH credentials were used or documented.

## القرار

Needs Fix

Recommended next step: run this benchmark on the Ubuntu AI server with Python 3.11/3.12 or a prepared container that already has PyTorch/CUDA dependencies installed.
