"""Regression test for the 2026-06-27 long-story timeout recovery fix.

Root cause (confirmed on Hamza's real "حين صار الخيال منصة" test, 8986 chars):
ComfyUI + AllTalk left too little VRAM for Ollama on the AI Server's 8GB GPU,
so Ollama silently fell back to CPU-only inference, and a flat
`num_predict=2500` per chunk then took longer than `OLLAMA_TIMEOUT_SECONDS`
to generate -- a real Timeout, not a frontend/connectivity bug. See
`docs/DECISION_LOG.md`'s 2026-06-27 entry for the full write-up.

This script never calls a real Ollama server -- it imports backend code
directly (same one-script exception documented in
`test_long_story_improve.py`) and uses a scripted `FakeProvider` to exercise
the chunking/adaptive-retry logic in isolation, deterministically, with zero
AI Server load. It never prints story/prompt content, only structural facts.
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.ai_providers.ollama import OllamaError, OllamaResult, OllamaTimeoutError  # noqa: E402
from app.story_engine.engine import (  # noqa: E402
    SHORT_STORY_NUM_PREDICT,
    StoryEngine,
    num_predict_for_chunk,
    split_failed_chunk_for_retry,
    split_text_into_chunks,
)

FORBIDDEN_PHRASE = "جرّب وضع تحسين القصص الطويلة"

_FILLER_PARAGRAPH = (
    "في ليلة من ليالي الشتاء الباردة، جلس الأطفال حول النار يستمعون إلى حكايات "
    "الراوي العجوز الذي كان يحمل فانوساً يضيء له الطريق بين القرى البعيدة.\n\n"
)


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        sys.exit(1)


class FakeProvider:
    """Scripted stand-in for OllamaProvider. `behaviors[i]` controls the i-th
    call (0-indexed): an Exception instance to raise, or a string/None to
    succeed with that result text (defaults to a call-index marker)."""

    def __init__(self, model: str = "qwen2.5:7b", timeout: int = 180) -> None:
        self.model = model
        self.timeout = timeout
        self.calls: list[dict] = []
        self.behaviors: list[object] = []

    def generate_text(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        num_ctx: int = 8192,
        num_predict: int | None = None,
    ) -> OllamaResult:
        call_index = len(self.calls)
        self.calls.append({"prompt_chars": len(prompt), "num_predict": num_predict})
        behavior = self.behaviors[call_index] if call_index < len(self.behaviors) else None
        if isinstance(behavior, Exception):
            raise behavior
        text = behavior if isinstance(behavior, str) else f"IMPROVED::{call_index}"
        return OllamaResult(text=text, latency_ms=5, model=self.model)


def build_story(target_len: int) -> str:
    parts: list[str] = []
    total = 0
    while total <= target_len:
        parts.append(_FILLER_PARAGRAPH)
        total += len(_FILLER_PARAGRAPH)
    return "".join(parts).strip()


def test_chunking_default_3000() -> None:
    """8986-char story (Hamza's real test length) must now split into 3+
    chunks with the new default (was 2 chunks at the old default of 6000)."""
    story = build_story(8986)
    chunks = split_text_into_chunks(story, 3000)
    reassembled_len = sum(len(c) for c in chunks)
    # Joining N chunks back with "\n\n" normalizes at most one paragraph-break
    # separator (2 chars) per boundary -- not real content loss, just the
    # same boundary character accounted for on one side instead of both.
    max_expected_diff = 2 * max(0, len(chunks) - 1)
    check("8986-char story: chunk_count >= 3 with new default 3000", len(chunks) >= 3)
    check("8986-char story: every chunk <= 3000 chars", all(len(c) <= 3000 for c in chunks))
    check(
        "8986-char story: no content lost beyond expected boundary normalization",
        (len(story) - reassembled_len) <= max_expected_diff,
    )
    print(f"[INFO] story_len={len(story)} chunk_count={len(chunks)} chunk_lengths={[len(c) for c in chunks]}")


def test_retry_split_long_run_on_sentence() -> None:
    """A pathological chunk with no paragraph/sentence/comma boundaries at
    all (one giant run-on with spaces, then one with none) must still split
    into multiple subchunks without losing any word/character."""
    word = "كلمة"
    spaced_text = ((word + " ") * 800).strip()
    pieces = split_failed_chunk_for_retry(spaced_text, max_chars=600)
    check("spaced run-on: split into multiple subchunks", len(pieces) > 1)
    check("spaced run-on: every piece <= max_chars", all(len(p) <= 600 for p in pieces))
    word_count_original = spaced_text.count(word)
    word_count_pieces = sum(p.count(word) for p in pieces)
    check("spaced run-on: every word preserved across subchunks", word_count_original == word_count_pieces)

    unbroken_text = "ك" * 5000  # zero whitespace, zero punctuation anywhere
    pieces2 = split_failed_chunk_for_retry(unbroken_text, max_chars=600)
    reassembled2 = "".join(pieces2)
    check("unbroken run-on: split into multiple subchunks (hard split fallback)", len(pieces2) > 1)
    check("unbroken run-on: every piece <= max_chars", all(len(p) <= 600 for p in pieces2))
    check("unbroken run-on: reassembled length matches original exactly", len(reassembled2) == len(unbroken_text))
    check("unbroken run-on: reassembled content matches original exactly", reassembled2 == unbroken_text)


def test_short_story_keeps_num_predict_2500() -> None:
    """Short stories (single-shot path) must be completely unaffected --
    same num_predict=2500, same call count, no retry machinery involved."""
    provider = FakeProvider()
    engine = StoryEngine(provider)
    short_story = "قصة قصيرة جداً عن راوٍ وفانوس قديم."
    improved_text, _latency_ms, chunk_count = engine.improve_narration_script(
        story_text=short_story, tone="هادئ", language="ar", chunk_chars=3000
    )
    check("short story: chunk_count == 1", chunk_count == 1)
    check("short story: exactly one Ollama call", len(provider.calls) == 1)
    check("short story: num_predict == SHORT_STORY_NUM_PREDICT (2500)", provider.calls[0]["num_predict"] == SHORT_STORY_NUM_PREDICT)
    check("short story: improved_text non-empty", bool(improved_text))


def test_adaptive_retry_on_chunk_timeout() -> None:
    """Simulates exactly Hamza's failure: a long story's first chunk times
    out. The engine must split it into subchunks, retry them (not the whole
    story), preserve order, and never reprocess the second chunk more than
    once."""
    chunk_chars = 600
    story = build_story(1100)  # deterministically yields 2 chunks at 600 chars
    chunks = split_text_into_chunks(story, chunk_chars)
    check("setup: story splits into exactly 2 top-level chunks", len(chunks) == 2)

    expected_subchunks = split_failed_chunk_for_retry(chunks[0], max_chars=max(400, len(chunks[0]) // 2))
    check("setup: failing chunk can itself be split into >1 subchunk", len(expected_subchunks) > 1)

    provider = FakeProvider(timeout=180)
    provider.behaviors = [OllamaTimeoutError(timeout_seconds=180, message="simulated timeout")]
    engine = StoryEngine(provider)

    notices: list[str] = []
    improved_text, _latency_ms, chunk_count = engine.improve_narration_script(
        story_text=story,
        tone="هادئ",
        language="ar",
        chunk_chars=chunk_chars,
        on_retry_notice=notices.append,
    )

    check("adaptive retry: chunk_count == 2 (top-level chunks unchanged)", chunk_count == 2)
    check("adaptive retry: exactly one retry notice fired", len(notices) == 1)
    check("adaptive retry: notice does NOT contain the forbidden long-story-mode phrase", FORBIDDEN_PHRASE not in notices[0])
    check("adaptive retry: notice mentions part 1 of 2", "الجزء 1 من 2" in notices[0])
    check("adaptive retry: notice mentions the timeout seconds (180)", "180" in notices[0])

    expected_total_calls = 1 + len(expected_subchunks) + 1  # failed attempt + subchunks + chunk 2
    check(
        f"adaptive retry: exactly {expected_total_calls} Ollama calls (no reprocessing)",
        len(provider.calls) == expected_total_calls,
    )

    markers = [int(m) for m in re.findall(r"IMPROVED::(\d+)", improved_text)]
    check("adaptive retry: result markers present and in ascending call order", markers == sorted(markers) and len(markers) > 0)
    check("adaptive retry: the failed first call's marker (0) is absent from the result", 0 not in markers)
    print(f"[INFO] total_calls={len(provider.calls)} subchunks={len(expected_subchunks)} markers={markers}")


def test_final_failure_message_after_subchunk_retry_exhausted() -> None:
    """If a subchunk still times out after its one retry, the job must fail
    with the specific Arabic message -- never the forbidden long-story-mode
    suggestion, and never an unhandled exception."""
    chunk_chars = 600
    story = build_story(1100)
    chunks = split_text_into_chunks(story, chunk_chars)
    expected_subchunks = split_failed_chunk_for_retry(chunks[0], max_chars=max(400, len(chunks[0]) // 2))

    provider = FakeProvider(timeout=180)
    # Call 0: chunk 1 first attempt -> timeout. Calls 1..N: every subchunk's
    # first attempt -> timeout too, forcing each into its retry attempt,
    # which also times out -- so the chunk can never recover.
    provider.behaviors = [OllamaTimeoutError(180, "t")] * (1 + len(expected_subchunks) * 2)

    engine = StoryEngine(provider)
    notices: list[str] = []
    raised: OllamaError | None = None
    try:
        engine.improve_narration_script(
            story_text=story, tone="هادئ", language="ar", chunk_chars=chunk_chars, on_retry_notice=notices.append
        )
    except OllamaError as exc:
        raised = exc

    check("final failure: an OllamaError was raised (job-level failure, not a crash)", raised is not None)
    message = str(raised)
    check("final failure: message does NOT contain the forbidden long-story-mode phrase", FORBIDDEN_PHRASE not in message)
    check("final failure: message explains a subchunk failed after splitting/retry", "تقسيمه إلى أجزاء أصغر" in message)
    check("final failure: message hints at possible CPU fallback", "CPU" in message)


def main() -> None:
    test_chunking_default_3000()
    test_retry_split_long_run_on_sentence()
    test_short_story_keeps_num_predict_2500()
    test_adaptive_retry_on_chunk_timeout()
    test_final_failure_message_after_subchunk_retry_exhausted()
    print("Long story timeout recovery test passed.")


if __name__ == "__main__":
    main()
