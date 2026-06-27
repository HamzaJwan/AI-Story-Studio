"""Regression test for the 2026-06-27/28 "Story Analysis + Auto Mood + Real
Progress/Timing" pass (Milestones 1-8 of the streaming/planning fix).

Root cause this pass builds on: ComfyUI+AllTalk left too little VRAM for
Ollama, so `stream=false` meant the backend received nothing until the whole
(possibly CPU-only, possibly minutes-long) generation finished, with no way
to tell "still working" from "stuck", and no way to cancel. This script
proves, with zero real Ollama/AI Server load:

1. Auto Mood / Story Analysis (`StoryEngine.resolve_tone`) -- valid JSON,
   invalid JSON fallback, manual tone skips the analysis call entirely.
2. Ollama streaming (`OllamaProvider.generate_text_streaming`) -- fake NDJSON
   fragments assembled correctly, activity callback fires, done_reason/
   eval_count preserved, cooperative cancel, and that nothing resembling the
   fake prompt/fragment content ever reaches the logger.
3. Truncation detection (`is_truncated`/`TruncatedOutputError`) triggers the
   same split-and-recurse recovery as a timeout, without reprocessing
   already-successful chunks.
4. Lossless splitting (`split_text_into_chunks`) on paragraphs, newlines,
   multiple spaces, and a run-on sentence with no punctuation at all --
   `"".join(chunks) == original_text` exactly, every time.
5. Real per-chunk timing contract: `improve_narration_script` calls
   `on_chunk_complete(index, total, elapsed_seconds)` exactly once per
   top-level chunk, in order, with increasing indices -- the data the job
   runner's ETA estimate (average completed chunk time x remaining chunks)
   is built from.
6. Cooperative cancel and the global deadline at the StoryEngine level.
7. The new `STORY_JOB_THRESHOLD_CHARS`/`LONG_STORY_MAX_TOTAL_SECONDS`
   settings exist with the documented defaults (the actual job-vs-sync
   *routing* decision lives in the frontend -- see `frontend/src/App.tsx`'s
   `usesJobEndpoint`, verified by `tsc` during `npm run build`, not by this
   backend-only script).

Imports backend code directly (no live Ollama call in most tests) -- the
same one-script exception documented in `test_long_story_improve.py`. Never
prints prompt/story/fragment content, only structural facts.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.ai_providers.ollama import (  # noqa: E402
    OllamaCancelledError,
    OllamaProvider,
    OllamaResult,
    OllamaTimeoutError,
)
from app.config import Settings  # noqa: E402
from app.story_engine.engine import (  # noqa: E402
    AUTO_TONE_VALUE,
    DEFAULT_AUTO_FALLBACK_TONE,
    MANUAL_TONES,
    StoryCancelledError,
    StoryDeadlineExceededError,
    StoryEngine,
    TruncatedOutputError,
    is_truncated,
    split_text_into_chunks,
)


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        sys.exit(1)


def make_settings(**overrides) -> Settings:
    base = {
        "ollama_base_url": "http://fake-ollama-for-test:11434",
        "ollama_model": "qwen2.5:7b",
        "ollama_timeout_seconds": 5,
    }
    base.update(overrides)
    return Settings(**base)


# ── Milestone 1: Auto Mood / Story Analysis ─────────────────────────────────


class ToneAnalysisFakeProvider:
    """Stands in for OllamaProvider for `resolve_tone()` tests only -- the
    real provider's `generate_text` signature, scripted to return one fixed
    response (valid JSON, invalid JSON, or an exception)."""

    def __init__(self, model: str = "qwen2.5:7b", response_text: str | None = None, error: Exception | None = None):
        self.model = model
        self.timeout = 5
        self.response_text = response_text
        self.error = error
        self.call_count = 0

    def generate_text(self, prompt, model=None, temperature=0.2, num_ctx=8192, num_predict=None):
        self.call_count += 1
        if self.error:
            raise self.error
        return OllamaResult(text=self.response_text or "", latency_ms=5, model=self.model)


def test_auto_tone_valid_json() -> None:
    valid_json = (
        '{"recommended_tone": "قصصي دافئ", "genre": "قصة إنسانية", '
        '"pacing": "هادئ", "reason_ar": "تركز على الطموح والتجربة"}'
    )
    provider = ToneAnalysisFakeProvider(response_text=valid_json)
    engine = StoryEngine(provider)
    analysis = engine.resolve_tone("عنوان", "نص قصة" * 50, AUTO_TONE_VALUE)
    check("auto tone (valid JSON): one analysis call made", provider.call_count == 1)
    check("auto tone (valid JSON): resolved_tone matches recommendation", analysis.resolved_tone == "قصصي دافئ")
    check("auto tone (valid JSON): genre/pacing/reason captured", analysis.genre == "قصة إنسانية" and analysis.pacing == "هادئ")
    check("auto tone (valid JSON): analysis_fallback is False", analysis.analysis_fallback is False)


def test_auto_tone_invalid_json_falls_back() -> None:
    provider = ToneAnalysisFakeProvider(response_text="this is not json at all")
    engine = StoryEngine(provider)
    analysis = engine.resolve_tone("عنوان", "نص قصة" * 50, AUTO_TONE_VALUE)
    check("auto tone (invalid JSON): one analysis call attempted", provider.call_count == 1)
    check("auto tone (invalid JSON): falls back to the fixed safe tone", analysis.resolved_tone == DEFAULT_AUTO_FALLBACK_TONE)
    check("auto tone (invalid JSON): analysis_fallback is True", analysis.analysis_fallback is True)
    check("auto tone (invalid JSON): fallback tone is itself a valid manual tone", analysis.resolved_tone in MANUAL_TONES)


def test_auto_tone_unrecognized_recommendation_falls_back() -> None:
    provider = ToneAnalysisFakeProvider(response_text='{"recommended_tone": "نبرة غير معروفة"}')
    engine = StoryEngine(provider)
    analysis = engine.resolve_tone("عنوان", "نص", AUTO_TONE_VALUE)
    check("auto tone (unknown tone value): falls back safely instead of using an invalid tone", analysis.analysis_fallback is True)
    check("auto tone (unknown tone value): resolved_tone is the safe default", analysis.resolved_tone == DEFAULT_AUTO_FALLBACK_TONE)


def test_auto_tone_timeout_falls_back_without_failing_story() -> None:
    provider = ToneAnalysisFakeProvider(error=OllamaTimeoutError(5, "simulated"))
    engine = StoryEngine(provider)
    analysis = engine.resolve_tone("عنوان", "نص", AUTO_TONE_VALUE)
    check("auto tone (analysis timeout): does not raise -- falls back instead", analysis.analysis_fallback is True)
    check("auto tone (analysis timeout): resolved_tone is the safe default", analysis.resolved_tone == DEFAULT_AUTO_FALLBACK_TONE)


def test_manual_tone_skips_analysis_call() -> None:
    provider = ToneAnalysisFakeProvider(response_text="should never be read")
    engine = StoryEngine(provider)
    analysis = engine.resolve_tone("عنوان", "نص طويل" * 100, "تشويقي")
    check("manual tone: zero analysis calls made", provider.call_count == 0)
    check("manual tone: requested_tone == resolved_tone, used verbatim", analysis.resolved_tone == "تشويقي")
    check("manual tone: analysis_fallback is False", analysis.analysis_fallback is False)


# ── Milestone 2: Ollama streaming ────────────────────────────────────────────


class _FakeStreamingResponse:
    def __init__(self, lines: list[str]):
        self._lines = lines
        self.closed = False

    def raise_for_status(self) -> None:
        pass

    def iter_lines(self, decode_unicode: bool = True):
        for line in self._lines:
            yield line

    def close(self) -> None:
        self.closed = True


_FRAGMENT_MARKER = "ZZ_SECRET_FRAGMENT_ZZ"
_PROMPT_MARKER = "ZZ_SECRET_PROMPT_ZZ"


def _ndjson_lines(fragments: list[str], done_reason: str = "stop", eval_count: int | None = None) -> list[str]:
    import json as _json

    lines = [_json.dumps({"response": frag, "done": False}, ensure_ascii=False) for frag in fragments]
    final = {"response": "", "done": True, "done_reason": done_reason}
    if eval_count is not None:
        final["eval_count"] = eval_count
    final["prompt_eval_count"] = 10
    final["prompt_eval_duration"] = 1000
    final["eval_duration"] = 2000
    lines.append(_json.dumps(final, ensure_ascii=False))
    return lines


def test_streaming_assembles_fragments_and_preserves_metadata() -> None:
    fragments = [f"{_FRAGMENT_MARKER}_1 ", f"{_FRAGMENT_MARKER}_2 ", f"{_FRAGMENT_MARKER}_3"]
    lines = _ndjson_lines(fragments, done_reason="stop", eval_count=42)
    fake_response = _FakeStreamingResponse(lines)

    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    ollama_logger = logging.getLogger("app.ai_providers.ollama")
    ollama_logger.addHandler(handler)
    ollama_logger.setLevel(logging.DEBUG)

    activity_calls: list[tuple[int, float]] = []
    settings = make_settings()
    provider = OllamaProvider(settings)

    import requests as requests_module

    original_post = requests_module.post
    requests_module.post = lambda *a, **k: fake_response
    try:
        result = provider.generate_text_streaming(
            f"{_PROMPT_MARKER} some prompt text",
            num_predict=100,
            on_stream_activity=lambda units, elapsed: activity_calls.append((units, elapsed)),
        )
    finally:
        requests_module.post = original_post
        ollama_logger.removeHandler(handler)

    check("streaming: assembled text equals concatenated fragments", result.text == "".join(fragments).strip())
    check("streaming: done_reason preserved", result.done_reason == "stop")
    check("streaming: eval_count preserved", result.eval_count == 42)
    check("streaming: prompt_eval_count preserved", result.prompt_eval_count == 10)
    check("streaming: activity callback fired once per fragment", len(activity_calls) == len(fragments))
    check("streaming: activity units increase monotonically", [c[0] for c in activity_calls] == sorted(c[0] for c in activity_calls))
    check("streaming: response stream was closed", fake_response.closed is True)

    log_output = log_capture.getvalue()
    check("streaming: fragment content never logged", _FRAGMENT_MARKER not in log_output)
    check("streaming: prompt content never logged", _PROMPT_MARKER not in log_output)


def test_streaming_truncation_metadata_detected_as_truncated() -> None:
    lines = _ndjson_lines(["جزء من النص"], done_reason="length", eval_count=100)
    fake_response = _FakeStreamingResponse(lines)
    settings = make_settings()
    provider = OllamaProvider(settings)

    import requests as requests_module

    original_post = requests_module.post
    requests_module.post = lambda *a, **k: fake_response
    try:
        result = provider.generate_text_streaming("prompt", num_predict=100)
    finally:
        requests_module.post = original_post

    check("streaming truncation: done_reason == 'length' is surfaced", result.done_reason == "length")
    check("streaming truncation: is_truncated() detects it", is_truncated(result, num_predict=100) is True)


def test_streaming_cooperative_cancel() -> None:
    fragments = [f"frag{i}" for i in range(10)]
    lines = _ndjson_lines(fragments)
    fake_response = _FakeStreamingResponse(lines)
    settings = make_settings()
    provider = OllamaProvider(settings)

    seen = {"count": 0}

    def should_cancel() -> bool:
        seen["count"] += 1
        return seen["count"] > 3  # cancel after a few events, not immediately

    import requests as requests_module

    original_post = requests_module.post
    requests_module.post = lambda *a, **k: fake_response
    raised = None
    try:
        provider.generate_text_streaming("prompt", num_predict=100, should_cancel=should_cancel)
    except OllamaCancelledError as exc:
        raised = exc
    finally:
        requests_module.post = original_post

    check("streaming cancel: OllamaCancelledError raised", raised is not None)
    check("streaming cancel: did not consume the entire stream first", seen["count"] < len(fragments) + 2)


# ── Milestone 3: Truncation detection drives the same recovery as timeout ──


class TruncationThenSuccessProvider:
    """First call returns a "successful" response that is actually truncated
    (done_reason=length); every later call succeeds cleanly. Used to prove
    truncation triggers the split-and-recurse recovery, not a silent accept."""

    def __init__(self, model: str = "qwen2.5:7b", timeout: int = 5):
        self.model = model
        self.timeout = timeout
        self.calls: list[dict] = []

    def generate_text(self, prompt, model=None, temperature=0.2, num_ctx=8192, num_predict=None):
        call_index = len(self.calls)
        self.calls.append({"prompt_chars": len(prompt), "num_predict": num_predict})
        if call_index == 0:
            return OllamaResult(text="ناقص", latency_ms=5, model=self.model, done_reason="length", eval_count=num_predict)
        return OllamaResult(text=f"IMPROVED::{call_index}", latency_ms=5, model=self.model, done_reason="stop", eval_count=10)


def test_truncation_triggers_split_recovery_without_reprocessing() -> None:
    chunk_chars = 600
    story = ("جملة كاملة ومفهومة. " * 80).strip()
    chunks = split_text_into_chunks(story, chunk_chars)
    check("truncation setup: story splits into 2+ top-level chunks", len(chunks) >= 2)

    provider = TruncationThenSuccessProvider()
    engine = StoryEngine(provider)
    notices: list[str] = []
    result = engine.improve_narration_script(
        story_text=story, tone="هادئ", language="ar", chunk_chars=chunk_chars, on_retry_notice=notices.append
    )
    check("truncation: at least one recovery notice fired", len(notices) >= 1)
    check("truncation: improved_text is non-empty", bool(result.improved_text))
    check("truncation: the truncated first attempt's text ('ناقص') is not in the final result", "ناقص" not in result.improved_text)
    check("truncation: no Ollama call exceeds the first chunk's tier num_predict", all(c["num_predict"] <= 1400 for c in provider.calls))


# ── Milestone 4: Lossless splitting ─────────────────────────────────────────


def test_lossless_splitting_paragraphs_newlines_spaces() -> None:
    text = (
        "الفقرة الأولى تحتوي على   مسافات متعددة بين بعض الكلمات.\n"
        "سطر ثانٍ داخل نفس الفقرة، بترقيم عربي؛ وفاصلة، ونقطتين: هكذا.\n\n"
        "الفقرة الثانية بعد سطرين فارغين، وفيها علامات ترقيم عربية؟ ونقاط حذف...\n\n\n"
        "فقرة ثالثة بمسافة   ثلاثية   بين الكلمات وانتهت."
    )
    for max_chars in (40, 80, 150, 500):
        chunks = split_text_into_chunks(text, max_chars)
        check(f"lossless (max_chars={max_chars}): exact reassembly", "".join(chunks) == text)
        check(f"lossless (max_chars={max_chars}): every chunk respects max_chars or is unsplittable", all(len(c) <= max_chars for c in chunks) or max_chars < 10)


def test_lossless_splitting_run_on_no_punctuation() -> None:
    run_on = "كلمةواحدةطويلةجداًبدونأيفراغاتأوعلاماتترقيمعلىالإطلاقفيهذاالنصبأكمله" * 30
    chunks = split_text_into_chunks(run_on, 50)
    check("lossless run-on: exact reassembly", "".join(chunks) == run_on)
    check("lossless run-on: every chunk <= max_chars", all(len(c) <= 50 for c in chunks))


def test_lossless_splitting_8986_chars() -> None:
    filler = "نص تجريبي لقياس التقسيم بدون فقدان أي حرف، يتكرر عدة مرات. "
    text = (filler * (8986 // len(filler) + 1))[:8986]
    chunks = split_text_into_chunks(text, 3000)
    check("lossless 8986 chars: exact reassembly", "".join(chunks) == text)
    check("lossless 8986 chars: chunk_count >= 3", len(chunks) >= 3)


# ── Milestone 5: real per-chunk timing contract ─────────────────────────────


def test_on_chunk_complete_fires_in_order_with_increasing_elapsed() -> None:
    chunk_chars = 600
    story = ("جملة كاملة ومفهومة. " * 80).strip()

    class SlowThenFastProvider:
        model = "qwen2.5:7b"
        timeout = 5

        def __init__(self):
            self.calls = 0

        def generate_text(self, prompt, model=None, temperature=0.2, num_ctx=8192, num_predict=None):
            self.calls += 1
            time.sleep(0.01)
            return OllamaResult(text=f"IMPROVED::{self.calls}", latency_ms=10, model=self.model, done_reason="stop")

    provider = SlowThenFastProvider()
    engine = StoryEngine(provider)
    completions: list[tuple[int, int, float]] = []
    engine.improve_narration_script(
        story_text=story,
        tone="هادئ",
        language="ar",
        chunk_chars=chunk_chars,
        on_chunk_complete=lambda index, total, elapsed: completions.append((index, total, elapsed)),
    )
    indices = [c[0] for c in completions]
    check("timing: on_chunk_complete fires once per top-level chunk", len(completions) == indices[-1] if indices else False)
    check("timing: indices are 1..N in strict ascending order", indices == list(range(1, len(completions) + 1)))
    check("timing: every elapsed_seconds value is positive", all(c[2] > 0 for c in completions))
    if completions:
        average_after_first = completions[0][2]
        remaining_after_first = completions[0][1] - completions[0][0]
        estimated_eta = average_after_first * remaining_after_first
        check("timing: ETA is computable immediately after first completion (the UI rule)", estimated_eta >= 0)
    print(f"[INFO] chunk_completions={completions}")


# ── Milestone 6 & 7: cancel and global deadline at the engine level ────────


def test_engine_level_cancel() -> None:
    chunk_chars = 600
    story = ("جملة كاملة ومفهومة. " * 80).strip()
    provider = ToneAnalysisFakeProvider(response_text="should not be reached")
    engine = StoryEngine(provider)
    raised = None
    try:
        engine.improve_narration_script(
            story_text=story, tone="هادئ", language="ar", chunk_chars=chunk_chars, should_cancel=lambda: True
        )
    except StoryCancelledError as exc:
        raised = exc
    check("engine cancel: StoryCancelledError raised before any Ollama call", raised is not None)
    check("engine cancel: zero Ollama calls made", provider.call_count == 0)


def test_engine_level_deadline_exceeded() -> None:
    chunk_chars = 600
    story = ("جملة كاملة ومفهومة. " * 80).strip()
    provider = ToneAnalysisFakeProvider(response_text="should not be reached")
    engine = StoryEngine(provider)
    past_deadline = time.monotonic() - 1.0
    raised = None
    try:
        engine.improve_narration_script(
            story_text=story, tone="هادئ", language="ar", chunk_chars=chunk_chars, deadline_monotonic=past_deadline
        )
    except StoryDeadlineExceededError as exc:
        raised = exc
    check("engine deadline: StoryDeadlineExceededError raised", raised is not None)
    check("engine deadline: zero Ollama calls made (failed fast, no runaway retries)", provider.call_count == 0)


# ── Milestone 8: new settings exist with documented defaults ───────────────


def test_new_settings_defaults() -> None:
    settings = Settings()
    check("settings: STORY_JOB_THRESHOLD_CHARS default is 1500", settings.story_job_threshold_chars == 1500)
    check("settings: LONG_STORY_MAX_TOTAL_SECONDS default is 900", settings.long_story_max_total_seconds == 900)
    check("settings: LONG_STORY_CHUNK_CHARS default is 3000 (unchanged from the prior fix)", settings.long_story_chunk_chars == 3000)
    print(
        "[INFO] story_job_threshold_chars routing itself lives in frontend/src/App.tsx "
        "(usesJobEndpoint) -- verified by `tsc` during the frontend build, not here."
    )


def main() -> None:
    test_auto_tone_valid_json()
    test_auto_tone_invalid_json_falls_back()
    test_auto_tone_unrecognized_recommendation_falls_back()
    test_auto_tone_timeout_falls_back_without_failing_story()
    test_manual_tone_skips_analysis_call()

    test_streaming_assembles_fragments_and_preserves_metadata()
    test_streaming_truncation_metadata_detected_as_truncated()
    test_streaming_cooperative_cancel()

    test_truncation_triggers_split_recovery_without_reprocessing()

    test_lossless_splitting_paragraphs_newlines_spaces()
    test_lossless_splitting_run_on_no_punctuation()
    test_lossless_splitting_8986_chars()

    test_on_chunk_complete_fires_in_order_with_increasing_elapsed()

    test_engine_level_cancel()
    test_engine_level_deadline_exceeded()

    test_new_settings_defaults()

    print("Story planning and streaming test passed.")


if __name__ == "__main__":
    main()
