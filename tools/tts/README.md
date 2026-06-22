# SILMA TTS Benchmark Tools

هذه الأدوات منفصلة عن تطبيق Phase 0.1. لا تضيف API للصوت ولا تغيّر الواجهة.

## Local venv

```powershell
python -m venv .venv-silma
.venv-silma\Scripts\python -m pip install --upgrade pip
.venv-silma\Scripts\python -m pip install silma-tts soundfile
.venv-silma\Scripts\python tools\tts\silma_benchmark.py
```

If Python local is not compatible, use the isolated Docker benchmark:

```powershell
docker build -f tools/tts/Dockerfile.silma -t ai-story-studio-silma-benchmark .
docker run --rm -v ${PWD}\data:/workspace/data ai-story-studio-silma-benchmark
```

## Optional env vars

- `REF_AUDIO`: مسار ملف reference voice مسموح استخدامه.
- `REF_TEXT`: النص المنطوق في ملف المرجع.
- `SILMA_OUTPUT_DIR`: مجلد مخرجات بديل.
- `SILMA_SPEED`: سرعة النطق، الافتراضي `1.0`.

المخرجات الافتراضية داخل `data/benchmarks/tts/silma/` وهي ignored في Git.
