# Codex Phase 0 Benchmark Prompt

نفذ فقط اختبار Benchmark ولا تبني تطبيق كامل.

## المطلوب
1. سكريبت Python يتصل بـ Ollama.
2. يقرأ قصة عربية من ملف `sample_story.txt`.
3. يطلب من Ollama تقسيمها إلى مشاهد.
4. يحفظ `data/projects/benchmark/scenes.json`.
5. يتحقق من JSON.
6. يطبع ملخص المشاهد.

## غير مسموح
- لا frontend.
- لا TTS.
- لا فيديو.
- لا Docker.
- لا DB.

## النجاح
```powershell
python scripts/check_utf8.py
python scripts/benchmark_ollama_split.py
```

يجب أن يظهر:
- عدد المشاهد.
- عنوان كل مشهد.
- ملف scenes.json محفوظ.
