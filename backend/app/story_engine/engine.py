from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.ai_providers.ollama import (
    OllamaCancelledError,
    OllamaError,
    OllamaProvider,
    OllamaResult,
    OllamaTimeoutError,
)
from app.schemas import Scene, SplitScenesData, SplitScenesRequest

logger = logging.getLogger(__name__)


class StoryEngineError(RuntimeError):
    pass


class StoryCancelledError(StoryEngineError):
    """Raised when the caller's `should_cancel()` returns True. Distinct from
    `StoryEngineError`'s other uses so the job runner can set status
    `cancelled` instead of `failed`."""


class StoryDeadlineExceededError(StoryEngineError):
    """Raised when the global wall-clock deadline (Milestone 7) is exceeded.
    Independent of the per-request read timeout -- this bounds the *total*
    time spent across all chunks/retries/splits for one story."""


class TruncatedOutputError(OllamaError):
    """Raised when an Ollama response completed successfully but was cut off
    by the output budget (`done_reason == "length"`, or `eval_count` reached
    `num_predict`) -- Milestone 3. A *policy* decision about a successful
    response, not a transport error, but kept as an `OllamaError` subclass so
    it flows through the exact same recovery path as a real timeout."""

    def __init__(self, done_reason: str | None, eval_count: int | None, num_predict: int):
        super().__init__(
            "توقف الرد قبل اكتمال النص (تجاوز الحد الأقصى للطول num_predict)."
        )
        self.done_reason = done_reason
        self.eval_count = eval_count
        self.num_predict = num_predict


# Output budget (num_predict) tuning -- root cause of the 2026-06-27 long-story
# timeout (Hamza's "حين صار الخيال منصة" test): ComfyUI (~4.6GB) + AllTalk
# (~1.9GB) left only ~1.2GB VRAM for Ollama, which silently fell back to
# CPU-only inference ("offloaded 0/29 layers to GPU"). A fixed num_predict=2500
# for every chunk meant the model had to keep generating for far longer than
# OLLAMA_TIMEOUT_SECONDS (180s) on CPU. Short stories are unaffected and keep
# the original budget; only multi-chunk long-story requests get a smaller,
# size-scaled budget so a CPU-only run still has a realistic chance to finish
# in time. Splitting a failed/truncated chunk into smaller pieces (below)
# naturally lowers this further at each recovery level -- no separate
# "retry at a lower budget" constant is needed.
SHORT_STORY_NUM_PREDICT = 2500

# How many extra levels of recovery splitting one top-level chunk may go
# through before giving up. Bounds total Ollama calls per chunk; the global
# deadline (Milestone 7) is the real backstop against runaway total time.
MAX_RECOVERY_DEPTH = 3


def num_predict_for_chunk(chunk_chars: int) -> int:
    """Output budget for one long-story chunk/subchunk, scaled down from the
    short-story default by how much text it contains -- a smaller chunk needs
    a smaller reply, and a smaller `num_predict` finishes sooner even when
    Ollama is running CPU-only."""
    if chunk_chars > 2500:
        return 1400
    if chunk_chars >= 1200:
        return 1200
    return 900


def is_truncated(result: OllamaResult, num_predict: int) -> bool:
    """Milestone 3: a non-empty response is not automatically a success --
    `done_reason == "length"` or `eval_count` reaching `num_predict` both mean
    the model was cut off mid-sentence, not that it finished naturally."""
    if result.done_reason == "length":
        return True
    if result.eval_count is not None and num_predict and result.eval_count >= num_predict:
        return True
    return False


# ── Lossless text splitting (Milestone 4) ───────────────────────────────────
#
# Uses a capturing group around each boundary pattern so `re.split()` returns
# the separator text itself as part of the result list, instead of discarding
# it. Every separator is folded back onto the piece before it, so
# `"".join(pieces) == text` holds exactly -- no newline, run of spaces, or
# punctuation mark is ever dropped or normalized to a single space.

_CHUNK_BOUNDARY_PATTERNS: tuple[str, ...] = (
    r"\n\s*\n",
    r"(?<=[.!?؟])\s+",
)

_RETRY_BOUNDARY_PATTERNS: tuple[str, ...] = (
    r"\n\s*\n",
    r"\n",
    r"(?<=[.!?؟])\s+",
    r"(?<=[،,])\s+",
    r"\s+",
)


def _split_with_boundaries(text: str, max_chars: int, patterns: list[str]) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    if not patterns:
        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]

    pattern, remaining = patterns[0], patterns[1:]
    tokens = re.split(f"({pattern})", text)
    pieces: list[str] = []
    for i in range(0, len(tokens), 2):
        content = tokens[i]
        separator = tokens[i + 1] if i + 1 < len(tokens) else ""
        piece = content + separator
        if piece:
            pieces.append(piece)
    if len(pieces) <= 1:
        return _split_with_boundaries(text, max_chars, remaining)

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = current + piece
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(piece) <= max_chars:
            current = piece
        else:
            chunks.extend(_split_with_boundaries(piece, max_chars, remaining))
            current = ""
    if current:
        chunks.append(current)
    return chunks


def split_text_into_chunks(text: str, max_chars: int) -> list[str]:
    """Split text into ordered chunks <= max_chars, preferring paragraph then
    sentence breaks, then a last-resort hard character split. Byte-exact:
    `"".join(split_text_into_chunks(text, n)) == text` always holds -- no
    newline, space, or punctuation mark is ever dropped or normalized."""
    return _split_with_boundaries(text, max_chars, list(_CHUNK_BOUNDARY_PATTERNS))


def split_failed_chunk_for_retry(text: str, max_chars: int) -> list[str]:
    """Lossless recovery split for one chunk/subchunk that timed out or was
    truncated. Tries progressively finer boundaries (paragraph, line,
    sentence end, comma, then any whitespace) before a hard character split
    that never drops a character. If the text is already <= max_chars (a
    small piece that still failed -- e.g. pure CPU-load, not text length)
    this forces one even midpoint split so there is still something smaller
    to retry, unless the text is too short to usefully split further."""
    pieces = _split_with_boundaries(text, max_chars, list(_RETRY_BOUNDARY_PATTERNS))
    if len(pieces) > 1:
        return pieces
    if len(text) < 40:
        return [text]
    midpoint = len(text) // 2
    return [text[:midpoint], text[midpoint:]]


_FINAL_TIMEOUT_FAILURE_AR = (
    "فشل تحسين جزء من القصة بعد تقسيمه إلى أجزاء أصغر. قد يكون الموديل يعمل على CPU "
    "بسبب ضغط GPU. جرّب لاحقاً بعد تحرير GPU أو قلّل طول النص."
)


def _recoverable_notice_ar(exc: OllamaError, part_index: int, total_parts: int) -> str:
    if isinstance(exc, OllamaTimeoutError):
        return (
            f"انتهت مهلة Ollama أثناء تحسين الجزء {part_index} من {total_parts}. النظام يعمل "
            f"بالفعل بوضع القصص الطويلة، لكن هذا الجزء استغرق أكثر من {exc.timeout_seconds} ثانية. "
            "سيتم تقسيم الجزء إلى أجزاء أصغر والمحاولة مرة أخرى."
        )
    if isinstance(exc, TruncatedOutputError):
        return (
            f"الرد على الجزء {part_index} من {total_parts} توقف قبل اكتمال النص (تجاوز الحد الأقصى "
            "للطول). سيتم تقسيم الجزء إلى أجزاء أصغر وإعادة المحاولة."
        )
    return f"حدث خطأ أثناء تحسين الجزء {part_index} من {total_parts}. سيتم تقسيمه وإعادة المحاولة."


# ── Auto Mood / Story Analysis (Milestone 1) ────────────────────────────────

AUTO_TONE_VALUE = "تلقائي"
MANUAL_TONES: tuple[str, ...] = ("عسكري هادئ", "وثائقي مؤثر", "قصصي دافئ", "تشويقي")
DEFAULT_AUTO_FALLBACK_TONE = "قصصي دافئ"
ANALYSIS_NUM_PREDICT = 120
ANALYSIS_HEAD_CHARS = 1000
ANALYSIS_TAIL_CHARS = 600


@dataclass
class ToneAnalysis:
    requested_tone: str
    resolved_tone: str
    genre: str | None = None
    pacing: str | None = None
    reason_ar: str | None = None
    analysis_fallback: bool = False


@dataclass
class ImproveResult:
    improved_text: str
    latency_ms: int
    chunk_count: int
    requested_tone: str
    resolved_tone: str
    genre: str | None = None
    pacing: str | None = None
    reason_ar: str | None = None
    analysis_fallback: bool = False


class StoryEngine:
    def __init__(self, provider: OllamaProvider):
        self.provider = provider

    # ── Public API ───────────────────────────────────────────────────────

    def resolve_tone(self, title: str, story_text: str, requested_tone: str) -> ToneAnalysis:
        """Milestone 1: if the user picked a manual tone, use it directly --
        no analysis call, no extra latency. Only "تلقائي" triggers one small
        analysis pass (title + first 1000 + last 600 chars, never the full
        story) capped at num_predict=120. Any failure (bad JSON, timeout,
        unexpected tone value) falls back to a fixed safe tone instead of
        failing the whole improve job -- never logs the story text."""
        if requested_tone != AUTO_TONE_VALUE:
            return ToneAnalysis(requested_tone=requested_tone, resolved_tone=requested_tone)

        head = story_text[:ANALYSIS_HEAD_CHARS]
        tail = story_text[-ANALYSIS_TAIL_CHARS:] if len(story_text) > ANALYSIS_HEAD_CHARS else ""
        prompt = self._build_tone_analysis_prompt(title, head, tail, len(story_text))
        try:
            result = self.provider.generate_text(prompt, temperature=0.2, num_predict=ANALYSIS_NUM_PREDICT)
            data = extract_json_object(result.text)
            if not isinstance(data, dict):
                raise ValueError("tone analysis response was not a JSON object")
            recommended = str(data.get("recommended_tone", "")).strip()
            if recommended not in MANUAL_TONES:
                raise ValueError("recommended_tone not in the allowed manual tone list")
            genre = str(data.get("genre") or "").strip() or None
            pacing = str(data.get("pacing") or "").strip() or None
            reason_ar = str(data.get("reason_ar") or "").strip() or None
            logger.info(
                "story_tone_analysis_ok input_chars=%s resolved_tone=%s pacing=%s model=%s",
                len(story_text),
                recommended,
                pacing,
                self.provider.model,
            )
            return ToneAnalysis(
                requested_tone=requested_tone,
                resolved_tone=recommended,
                genre=genre,
                pacing=pacing,
                reason_ar=reason_ar,
                analysis_fallback=False,
            )
        except (OllamaError, ValueError, TypeError) as exc:
            logger.info(
                "story_tone_analysis_fallback analysis_fallback=true input_chars=%s error_class=%s",
                len(story_text),
                type(exc).__name__,
            )
            return ToneAnalysis(
                requested_tone=requested_tone,
                resolved_tone=DEFAULT_AUTO_FALLBACK_TONE,
                analysis_fallback=True,
            )

    def improve_narration_script(
        self,
        story_text: str,
        tone: str,
        language: str,
        chunk_chars: int = 3000,
        title: str = "",
        on_progress: Callable[[int, int], None] | None = None,
        on_retry_notice: Callable[[str], None] | None = None,
        on_chunk_complete: Callable[[int, int, float], None] | None = None,
        on_stream_activity: Callable[[int, float], None] | None = None,
        on_tone_resolved: Callable[[ToneAnalysis], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
        deadline_monotonic: float | None = None,
        use_streaming: bool = False,
    ) -> ImproveResult:
        """Improve a narration script, splitting into ordered chunks when long.

        A single Ollama request with a very long prompt (10k+ Arabic
        characters) is the original manual-QA failure: it tends to time out
        or get rejected by the model's context window, and that failure was
        previously misreported as a generic connection error. Splitting on
        paragraph/sentence boundaries keeps each request small and fast, and
        chunks are improved in order so the narration stays sequential. No
        extra "merge/smoothing" pass is run afterwards -- that would just
        reintroduce one long prompt over the whole improved text, the exact
        problem being fixed here.

        `on_retry_notice`, if given, is called with a ready Arabic status
        string the moment a chunk times out/truncates and adaptive recovery
        begins -- the job system wires this to the job's live `message_ar`.
        `on_chunk_complete`/`on_stream_activity` feed the job's real progress
        and timing fields (Milestone 5). `should_cancel`/`deadline_monotonic`
        are checked at every safe point (Milestones 6/7). `use_streaming`
        is only ever True for the job-based path -- the single-shot
        synchronous endpoint keeps its original, unchanged behavior.
        """
        tone_analysis = self.resolve_tone(title, story_text, tone)
        resolved_tone = tone_analysis.resolved_tone
        if on_tone_resolved:
            on_tone_resolved(tone_analysis)

        if len(story_text) <= chunk_chars:
            prompt = self._build_improve_prompt(story_text, resolved_tone, language)
            result = self._call_with_telemetry(
                prompt,
                SHORT_STORY_NUM_PREDICT,
                part_index=1,
                total_parts=1,
                retry_attempt=0,
                use_streaming=use_streaming,
                on_stream_activity=on_stream_activity,
                should_cancel=should_cancel,
            )
            return ImproveResult(
                improved_text=result.text,
                latency_ms=result.latency_ms,
                chunk_count=1,
                requested_tone=tone_analysis.requested_tone,
                resolved_tone=resolved_tone,
                genre=tone_analysis.genre,
                pacing=tone_analysis.pacing,
                reason_ar=tone_analysis.reason_ar,
                analysis_fallback=tone_analysis.analysis_fallback,
            )

        chunks = split_text_into_chunks(story_text, chunk_chars)
        logger.info(
            "story_improve_start input_chars=%s chunk_count=%s chunk_lengths=%s model=%s resolved_tone=%s",
            len(story_text),
            len(chunks),
            [len(c) for c in chunks],
            self.provider.model,
            resolved_tone,
        )
        improved_parts: list[str] = []
        total_latency = 0
        for index, chunk in enumerate(chunks, start=1):
            self._check_cancel_and_deadline(should_cancel, deadline_monotonic)
            if on_progress:
                on_progress(index, len(chunks))
            chunk_started = time.perf_counter()
            improved_text, latency_ms = self._improve_text_with_recovery(
                chunk,
                resolved_tone,
                language,
                part_index=index,
                total_parts=len(chunks),
                depth=0,
                on_retry_notice=on_retry_notice,
                on_stream_activity=on_stream_activity,
                should_cancel=should_cancel,
                deadline_monotonic=deadline_monotonic,
                use_streaming=use_streaming,
            )
            total_latency += latency_ms
            improved_parts.append(improved_text)
            if on_chunk_complete:
                on_chunk_complete(index, len(chunks), time.perf_counter() - chunk_started)
        return ImproveResult(
            improved_text="\n\n".join(improved_parts),
            latency_ms=total_latency,
            chunk_count=len(chunks),
            requested_tone=tone_analysis.requested_tone,
            resolved_tone=resolved_tone,
            genre=tone_analysis.genre,
            pacing=tone_analysis.pacing,
            reason_ar=tone_analysis.reason_ar,
            analysis_fallback=tone_analysis.analysis_fallback,
        )

    # ── Internal helpers ─────────────────────────────────────────────────

    def _check_cancel_and_deadline(
        self,
        should_cancel: Callable[[], bool] | None,
        deadline_monotonic: float | None,
    ) -> None:
        if should_cancel and should_cancel():
            raise StoryCancelledError("تم إلغاء تحسين القصة.")
        if deadline_monotonic is not None and time.monotonic() > deadline_monotonic:
            raise StoryDeadlineExceededError(
                "تجاوز تحسين القصة الحد الأقصى المسموح للعملية. تم إيقافها حتى لا تبقى معلقة."
            )

    def _call_with_telemetry(
        self,
        prompt: str,
        num_predict: int,
        *,
        part_index: int,
        total_parts: int,
        retry_attempt: int,
        use_streaming: bool = False,
        on_stream_activity: Callable[[int, float], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> OllamaResult:
        """Single Ollama call with safe, content-free telemetry logging and
        truncation detection (Milestone 3). Never logs the prompt or story
        text itself -- only structural facts (lengths, timing, model, error
        class, done_reason, eval_count)."""
        started = time.perf_counter()
        try:
            if use_streaming:
                result = self.provider.generate_text_streaming(
                    prompt,
                    temperature=0.25,
                    num_predict=num_predict,
                    on_stream_activity=on_stream_activity,
                    should_cancel=should_cancel,
                )
            else:
                result = self.provider.generate_text(prompt, temperature=0.25, num_predict=num_predict)
        except OllamaCancelledError as exc:
            raise StoryCancelledError("تم إلغاء تحسين القصة.") from exc
        except OllamaError as exc:
            elapsed_seconds = time.perf_counter() - started
            logger.info(
                "story_improve_call_failed part_index=%s total_parts=%s prompt_chars=%s "
                "num_predict=%s timeout_seconds=%s elapsed_seconds=%.1f model=%s "
                "error_class=%s retry_attempt=%s",
                part_index,
                total_parts,
                len(prompt),
                num_predict,
                self.provider.timeout,
                elapsed_seconds,
                self.provider.model,
                type(exc).__name__,
                retry_attempt,
            )
            raise
        elapsed_seconds = time.perf_counter() - started
        truncated = is_truncated(result, num_predict)
        logger.info(
            "story_improve_call_ok part_index=%s total_parts=%s prompt_chars=%s num_predict=%s "
            "elapsed_seconds=%.1f model=%s retry_attempt=%s done_reason=%s eval_count=%s "
            "output_chars=%s truncation_detected=%s",
            part_index,
            total_parts,
            len(prompt),
            num_predict,
            elapsed_seconds,
            self.provider.model,
            retry_attempt,
            result.done_reason,
            result.eval_count,
            len(result.text),
            truncated,
        )
        if truncated:
            raise TruncatedOutputError(result.done_reason, result.eval_count, num_predict)
        return result

    def _improve_text_with_recovery(
        self,
        text: str,
        tone: str,
        language: str,
        part_index: int,
        total_parts: int,
        *,
        depth: int,
        on_retry_notice: Callable[[str], None] | None,
        on_stream_activity: Callable[[int, float], None] | None,
        should_cancel: Callable[[], bool] | None,
        deadline_monotonic: float | None,
        use_streaming: bool,
        subpart_index: int | None = None,
        subpart_total: int | None = None,
    ) -> tuple[str, int]:
        """Improve one piece of text (a top-level chunk at depth 0, or a
        recovery subchunk at depth > 0). On `OllamaTimeoutError` or
        `TruncatedOutputError`, do not fail the whole story -- split just
        this piece into smaller pieces and recurse (bounded by
        `MAX_RECOVERY_DEPTH`). A piece that already succeeded is never
        reprocessed: each piece is attempted exactly once per recursion call,
        and recursion only ever happens on the piece that just failed."""
        self._check_cancel_and_deadline(should_cancel, deadline_monotonic)
        prompt = self._build_improve_prompt(
            text, tone, language, part_index, total_parts, subpart_index, subpart_total
        )
        num_predict = num_predict_for_chunk(len(text))
        try:
            result = self._call_with_telemetry(
                prompt,
                num_predict,
                part_index=part_index,
                total_parts=total_parts,
                retry_attempt=depth,
                use_streaming=use_streaming,
                on_stream_activity=on_stream_activity,
                should_cancel=should_cancel,
            )
            return result.text, result.latency_ms
        except (OllamaTimeoutError, TruncatedOutputError) as exc:
            if on_retry_notice:
                on_retry_notice(_recoverable_notice_ar(exc, part_index, total_parts))
            if depth >= MAX_RECOVERY_DEPTH:
                raise OllamaError(_FINAL_TIMEOUT_FAILURE_AR) from exc
            pieces = split_failed_chunk_for_retry(text, max_chars=max(400, len(text) // 2))
            if len(pieces) <= 1:
                raise OllamaError(_FINAL_TIMEOUT_FAILURE_AR) from exc

            improved_parts: list[str] = []
            total_latency = 0
            for sub_index, piece in enumerate(pieces, start=1):
                piece_text, piece_latency = self._improve_text_with_recovery(
                    piece,
                    tone,
                    language,
                    part_index,
                    total_parts,
                    depth=depth + 1,
                    on_retry_notice=on_retry_notice,
                    on_stream_activity=on_stream_activity,
                    should_cancel=should_cancel,
                    deadline_monotonic=deadline_monotonic,
                    use_streaming=use_streaming,
                    subpart_index=sub_index,
                    subpart_total=len(pieces),
                )
                improved_parts.append(piece_text)
                total_latency += piece_latency
            return "\n\n".join(improved_parts), total_latency

    def _build_tone_analysis_prompt(self, title: str, head: str, tail: str, total_chars: int) -> str:
        tail_section = f"\nنهاية القصة (آخر {len(tail)} حرف): {tail}" if tail else ""
        return f"""
أنت محلل أدبي يقترح أسلوب سرد مناسب لقصة عربية، بدون كتابة القصة نفسها.
العنوان: {title or "بدون عنوان"}
إجمالي عدد أحرف القصة: {total_chars}
بداية القصة (أول {len(head)} حرف): {head}{tail_section}

أرجع JSON فقط بهذا الشكل بالضبط، بدون أي شرح إضافي:
{{
  "recommended_tone": "عسكري هادئ أو وثائقي مؤثر أو قصصي دافئ أو تشويقي",
  "genre": "وصف عربي قصير لنوع القصة",
  "pacing": "هادئ أو متوسط أو سريع",
  "reason_ar": "سبب مختصر لا يتجاوز جملة واحدة"
}}
""".strip()

    def _build_improve_prompt(
        self,
        story_text: str,
        tone: str,
        language: str,
        part_index: int | None = None,
        total_parts: int | None = None,
        subpart_index: int | None = None,
        subpart_total: int | None = None,
    ) -> str:
        continuation_note = ""
        if subpart_index and subpart_total and subpart_total > 1:
            continuation_note = (
                f"\n- هذا المقطع الفرعي {subpart_index} من {subpart_total} داخل الجزء "
                f"{part_index} من {total_parts} من قصة طويلة مقسّمة. تابع نفس الأسلوب والمعنى "
                "بالضبط، ولا تبدأ مقدمة جديدة ولا تكتب خاتمة، باعتباره استمراراً مباشراً لما قبله."
            )
        elif total_parts and total_parts > 1:
            continuation_note = (
                f"\n- هذا الجزء {part_index} من {total_parts} من قصة طويلة مقسّمة. حسّن هذا الجزء "
                "فقط بنفس الأسلوب، ولا تكتب مقدمة أو خاتمة منفصلة له، باعتباره استمراراً لما قبله."
            )
        return f"""
أنت محرر سرد عربي محترف.
حوّل النص التالي إلى سكريبت راوي عربي فصيح ومناسب للقراءة الصوتية.

القواعد:
- حافظ على المعنى الأصلي.
- لا تضف أحداثاً غير موجودة.
- لا تغيّر أسماء الأشخاص أو الأماكن.
- اجعل الأسلوب: {tone}.
- أعد النص المحسن فقط دون عناوين أو شرح.
- اللغة المطلوبة: {language}.{continuation_note}

النص:
{story_text}
""".strip()

    def split_into_scenes(self, request: SplitScenesRequest) -> tuple[SplitScenesData, int]:
        last_error = "Unknown JSON parsing error."
        total_latency = 0
        for attempt in range(2):
            prompt = self._build_split_prompt(request, strict=attempt > 0)
            result = self.provider.generate_text(prompt, temperature=0.15, num_predict=3500)
            total_latency += result.latency_ms
            try:
                raw_data = extract_json_object(result.text)
                normalized = normalize_scenes_payload(raw_data, request)
                return normalized, total_latency
            except (ValueError, ValidationError) as exc:
                last_error = str(exc)

        raise StoryEngineError(
            f"Could not extract valid scenes JSON from Ollama after 2 attempts: {last_error}"
        )

    def _build_split_prompt(self, request: SplitScenesRequest, strict: bool) -> str:
        strict_note = "لا تستخدم markdown ولا code fences. JSON فقط." if strict else "أرجع JSON فقط قدر الإمكان."
        return f"""
أنت مخطط مشاهد لقصة عربية.
قسّم القصة إلى {request.target_scenes} مشاهد واضحة ومناسبة لاحقاً للسرد والصور.

القواعد:
- {strict_note}
- لا تنفذ صوراً ولا صوتاً.
- لا تضف أحداثاً غير موجودة في القصة.
- اجعل narration_ar عربياً فصيحاً ومناسباً للراوي.
- اجعل image_prompt_en إنجليزياً، سينمائياً، ومفيداً لاحقاً لتوليد صورة ثابتة.
- مدة كل مشهد بين 6 و20 ثانية.
- استخدم scene_id مثل "01", "02".
- الأسلوب: {request.tone}.

الشكل المطلوب بدقة:
{{
  "story_title": "{request.title}",
  "scenes": [
    {{
      "scene_id": "01",
      "title_ar": "عنوان عربي قصير",
      "narration_ar": "نص الراوي",
      "visual_description_ar": "وصف بصري عربي",
      "image_prompt_en": "cinematic realistic scene, ...",
      "duration_seconds": 8
    }}
  ]
}}

القصة:
{request.story_text}
""".strip()


def extract_json_object(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "```").strip()
        parts = cleaned.split("```")
        if len(parts) >= 3:
            cleaned = parts[1].strip()

    start = cleaned.find("{")
    if start == -1:
        start = cleaned.find("[")
    if start == -1:
        raise ValueError("No JSON object or array found in model response.")

    opening = cleaned[start]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                candidate = cleaned[start : index + 1]
                return json.loads(candidate)

    raise ValueError("JSON response was incomplete.")


def normalize_scenes_payload(raw_data: Any, request: SplitScenesRequest) -> SplitScenesData:
    if isinstance(raw_data, list):
        raw_data = {"story_title": request.title, "scenes": raw_data}
    if not isinstance(raw_data, dict):
        raise ValueError("Scenes JSON root must be an object.")
    if "data" in raw_data and isinstance(raw_data["data"], dict):
        raw_data = raw_data["data"]

    scenes = raw_data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Scenes JSON must include a non-empty scenes array.")

    normalized_scenes = []
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise ValueError("Each scene must be an object.")
        scene.setdefault("scene_id", f"{index:02d}")
        scene["scene_id"] = str(scene["scene_id"]).zfill(2)
        scene.setdefault("duration_seconds", 8)
        normalized_scenes.append(Scene.model_validate(scene))

    return SplitScenesData(
        story_title=str(raw_data.get("story_title") or request.title or "قصة جديدة"),
        scenes=normalized_scenes,
    )
