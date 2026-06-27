from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from app.ai_providers.ollama import OllamaError, OllamaProvider, OllamaResult, OllamaTimeoutError
from app.schemas import Scene, SplitScenesData, SplitScenesRequest

logger = logging.getLogger(__name__)


class StoryEngineError(RuntimeError):
    pass


# Output budget (num_predict) tuning -- root cause of the 2026-06-27 long-story
# timeout (Hamza's "حين صار الخيال منصة" test): ComfyUI (~4.6GB) + AllTalk
# (~1.9GB) left only ~1.2GB VRAM for Ollama, which silently fell back to
# CPU-only inference ("offloaded 0/29 layers to GPU"). A fixed num_predict=2500
# for every chunk meant the model had to keep generating for far longer than
# OLLAMA_TIMEOUT_SECONDS (180s) on CPU. Short stories are unaffected and keep
# the original budget; only multi-chunk long-story requests get a smaller,
# size-scaled budget so a CPU-only run still has a realistic chance to finish
# in time, and an even smaller budget on the one-time subchunk retry below.
SHORT_STORY_NUM_PREDICT = 2500


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


def retry_num_predict_for_chunk(chunk_chars: int) -> int:
    """Strictly lower output budget for a subchunk's single retry attempt,
    used only after that exact subchunk already timed out once at
    `num_predict_for_chunk(chunk_chars)`."""
    return max(500, num_predict_for_chunk(chunk_chars) - 400)


# Recovery-split boundaries, finest-grained last, tried in order against a
# chunk that just raised OllamaTimeoutError -- paragraph, then line, then
# sentence end, then comma, then any whitespace, before a last-resort hard
# character split that never drops a character.
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
    pieces = [p for p in re.split(pattern, text) if p]
    if len(pieces) <= 1:
        return _split_with_boundaries(text, max_chars, remaining)

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = f"{current} {piece}" if current else piece
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


def split_failed_chunk_for_retry(text: str, max_chars: int) -> list[str]:
    """Lossless recovery split for one chunk that raised `OllamaTimeoutError`.
    Tries progressively finer boundaries (paragraph, line, sentence end,
    comma, then any whitespace) before a hard character split that never
    drops a character. If the text is already <= max_chars (a small chunk
    that still timed out -- e.g. pure CPU-load, not text length) this forces
    one even midpoint split so there is still something smaller to retry,
    unless the text is too short to usefully split further."""
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


def _build_retry_notice_ar(part_index: int, total_parts: int, timeout_seconds: int) -> str:
    return (
        f"انتهت مهلة Ollama أثناء تحسين الجزء {part_index} من {total_parts}. النظام يعمل "
        f"بالفعل بوضع القصص الطويلة، لكن هذا الجزء استغرق أكثر من {timeout_seconds} ثانية. "
        "سيتم تقسيم الجزء إلى أجزاء أصغر والمحاولة مرة أخرى."
    )


class StoryEngine:
    def __init__(self, provider: OllamaProvider):
        self.provider = provider

    def improve_narration_script(
        self,
        story_text: str,
        tone: str,
        language: str,
        chunk_chars: int = 3000,
        on_progress: Callable[[int, int], None] | None = None,
        on_retry_notice: Callable[[str], None] | None = None,
    ) -> tuple[str, int, int]:
        """Improve a narration script, splitting into ordered chunks when long.

        Returns (improved_text, total_latency_ms, chunk_count). A single Ollama
        request with a very long prompt (10k+ Arabic characters) is the original
        manual-QA failure: it tends to time out or get rejected by the model's
        context window, and that failure was previously misreported as a generic
        connection error. Splitting on paragraph/sentence boundaries keeps each
        request small and fast, and chunks are improved in order so the narration
        stays sequential. No extra "merge/smoothing" pass is run afterwards --
        that would just reintroduce one long prompt over the whole improved text,
        the exact problem being fixed here.

        `on_retry_notice`, if given, is called with a ready Arabic status string
        the moment a chunk times out and adaptive subchunk recovery begins (see
        `_improve_chunk_with_retry`) -- the job system wires this to the job's
        live `message_ar` so the user sees what is happening instead of a silent
        wait. The single-shot (short story) path below intentionally does not
        use this recovery -- short stories keep their original, unchanged
        behavior and error path.
        """
        if len(story_text) <= chunk_chars:
            prompt = self._build_improve_prompt(story_text, tone, language)
            result = self._call_with_telemetry(
                prompt, SHORT_STORY_NUM_PREDICT, part_index=1, total_parts=1, retry_attempt=0
            )
            return result.text, result.latency_ms, 1

        chunks = split_text_into_chunks(story_text, chunk_chars)
        logger.info(
            "story_improve_start input_chars=%s chunk_count=%s chunk_lengths=%s model=%s",
            len(story_text),
            len(chunks),
            [len(c) for c in chunks],
            self.provider.model,
        )
        improved_parts: list[str] = []
        total_latency = 0
        for index, chunk in enumerate(chunks, start=1):
            if on_progress:
                on_progress(index, len(chunks))
            improved_text, latency_ms = self._improve_chunk_with_retry(
                chunk,
                tone,
                language,
                part_index=index,
                total_parts=len(chunks),
                on_retry_notice=on_retry_notice,
            )
            total_latency += latency_ms
            improved_parts.append(improved_text)
        return "\n\n".join(improved_parts), total_latency, len(chunks)

    def _call_with_telemetry(
        self,
        prompt: str,
        num_predict: int,
        *,
        part_index: int,
        total_parts: int,
        retry_attempt: int,
    ) -> OllamaResult:
        """Single Ollama call with safe, content-free telemetry logging. Never
        logs the prompt or story text itself -- only structural facts (lengths,
        timing, model, error class)."""
        started = time.perf_counter()
        try:
            result = self.provider.generate_text(prompt, temperature=0.25, num_predict=num_predict)
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
        logger.info(
            "story_improve_call_ok part_index=%s total_parts=%s prompt_chars=%s num_predict=%s "
            "elapsed_seconds=%.1f model=%s retry_attempt=%s",
            part_index,
            total_parts,
            len(prompt),
            num_predict,
            elapsed_seconds,
            self.provider.model,
            retry_attempt,
        )
        return result

    def _improve_chunk_with_retry(
        self,
        chunk: str,
        tone: str,
        language: str,
        part_index: int,
        total_parts: int,
        on_retry_notice: Callable[[str], None] | None = None,
    ) -> tuple[str, int]:
        """Improve one long-story chunk. On `OllamaTimeoutError`, do not fail
        the whole story -- split just this chunk into smaller subchunks and
        retry each individually (at most one retry per subchunk, at a lower
        `num_predict`). Chunks that already succeeded are never reprocessed:
        this function is only ever called once per chunk from the loop above."""
        prompt = self._build_improve_prompt(chunk, tone, language, part_index, total_parts)
        num_predict = num_predict_for_chunk(len(chunk))
        try:
            result = self._call_with_telemetry(
                prompt, num_predict, part_index=part_index, total_parts=total_parts, retry_attempt=0
            )
            return result.text, result.latency_ms
        except OllamaTimeoutError as exc:
            if on_retry_notice:
                on_retry_notice(_build_retry_notice_ar(part_index, total_parts, exc.timeout_seconds))

        subchunks = split_failed_chunk_for_retry(chunk, max_chars=max(400, len(chunk) // 2))
        if len(subchunks) <= 1:
            # Could not split this chunk into anything smaller -- splitting
            # further would not help a CPU/GPU-load timeout, so stop here
            # with a clear message instead of looping forever.
            raise OllamaError(_FINAL_TIMEOUT_FAILURE_AR)

        improved_parts: list[str] = []
        total_latency = 0
        for subchunk in subchunks:
            sub_prompt = self._build_improve_prompt(subchunk, tone, language, part_index, total_parts)
            sub_num_predict = num_predict_for_chunk(len(subchunk))
            try:
                result = self._call_with_telemetry(
                    sub_prompt,
                    sub_num_predict,
                    part_index=part_index,
                    total_parts=total_parts,
                    retry_attempt=0,
                )
            except OllamaTimeoutError:
                retry_num_predict = retry_num_predict_for_chunk(len(subchunk))
                try:
                    result = self._call_with_telemetry(
                        sub_prompt,
                        retry_num_predict,
                        part_index=part_index,
                        total_parts=total_parts,
                        retry_attempt=1,
                    )
                except OllamaTimeoutError as exc:
                    raise OllamaError(_FINAL_TIMEOUT_FAILURE_AR) from exc
            improved_parts.append(result.text)
            total_latency += result.latency_ms
        return "\n\n".join(improved_parts), total_latency

    def _build_improve_prompt(
        self,
        story_text: str,
        tone: str,
        language: str,
        part_index: int | None = None,
        total_parts: int | None = None,
    ) -> str:
        continuation_note = ""
        if total_parts and total_parts > 1:
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


def split_text_into_chunks(text: str, max_chars: int) -> list[str]:
    """Split text into ordered chunks <= max_chars, preferring paragraph then sentence breaks."""
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(paragraph) <= max_chars:
            current = paragraph
            continue
        sentence_chunks = _split_long_paragraph(paragraph, max_chars)
        chunks.extend(sentence_chunks[:-1])
        current = sentence_chunks[-1] if sentence_chunks else ""
    if current:
        chunks.append(current)
    return chunks


def _split_long_paragraph(paragraph: str, max_chars: int) -> list[str]:
    """Split one long paragraph by sentence boundary; if a single "sentence"
    (a run-on with no `.!?؟` anywhere) is itself longer than max_chars, hard-
    split it into max_chars-sized pieces instead of truncating. Losing
    narration text is worse than sending one oversized chunk to Ollama --
    this function must never drop any input character.
    """
    sentences = [s for s in re.split(r"(?<=[.!?؟])\s+", paragraph) if s]
    if not sentences:
        sentences = [paragraph]

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}" if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(sentence) <= max_chars:
            current = sentence
            continue
        # No normal punctuation inside this "sentence" either -- hard-split into
        # max_chars-sized pieces so every character still ends up in some chunk.
        for start in range(0, len(sentence), max_chars):
            piece = sentence[start : start + max_chars]
            if start + max_chars >= len(sentence):
                current = piece
            else:
                chunks.append(piece)
    if current:
        chunks.append(current)
    return chunks


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
