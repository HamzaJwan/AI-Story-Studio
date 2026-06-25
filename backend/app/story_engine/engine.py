from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from app.ai_providers.ollama import OllamaProvider
from app.schemas import Scene, SplitScenesData, SplitScenesRequest


class StoryEngineError(RuntimeError):
    pass


class StoryEngine:
    def __init__(self, provider: OllamaProvider):
        self.provider = provider

    def improve_narration_script(
        self,
        story_text: str,
        tone: str,
        language: str,
        chunk_chars: int = 6000,
        on_progress: Callable[[int, int], None] | None = None,
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
        """
        if len(story_text) <= chunk_chars:
            prompt = self._build_improve_prompt(story_text, tone, language)
            result = self.provider.generate_text(prompt, temperature=0.25, num_predict=2500)
            return result.text, result.latency_ms, 1

        chunks = split_text_into_chunks(story_text, chunk_chars)
        improved_parts: list[str] = []
        total_latency = 0
        for index, chunk in enumerate(chunks, start=1):
            if on_progress:
                on_progress(index, len(chunks))
            prompt = self._build_improve_prompt(
                chunk, tone, language, part_index=index, total_parts=len(chunks)
            )
            result = self.provider.generate_text(prompt, temperature=0.25, num_predict=2500)
            total_latency += result.latency_ms
            improved_parts.append(result.text)
        return "\n\n".join(improved_parts), total_latency, len(chunks)

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
    sentences = [s for s in re.split(r"(?<=[.!?؟])\s+", paragraph) if s]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}" if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        # A single sentence longer than max_chars is a rare edge case (no normal
        # punctuation) -- hard-cut it so this function always terminates.
        current = sentence[:max_chars] if len(sentence) > max_chars else sentence
    if current:
        chunks.append(current)
    return chunks or [paragraph[:max_chars]]


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
