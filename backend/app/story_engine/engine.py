from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.ai_providers.ollama import OllamaProvider
from app.schemas import Scene, SplitScenesData, SplitScenesRequest


class StoryEngineError(RuntimeError):
    pass


class StoryEngine:
    def __init__(self, provider: OllamaProvider):
        self.provider = provider

    def improve_narration_script(self, story_text: str, tone: str, language: str) -> tuple[str, int]:
        prompt = f"""
أنت محرر سرد عربي محترف.
حوّل النص التالي إلى سكريبت راوي عربي فصيح ومناسب للقراءة الصوتية.

القواعد:
- حافظ على المعنى الأصلي.
- لا تضف أحداثاً غير موجودة.
- لا تغيّر أسماء الأشخاص أو الأماكن.
- اجعل الأسلوب: {tone}.
- أعد النص المحسن فقط دون عناوين أو شرح.
- اللغة المطلوبة: {language}.

النص:
{story_text}
""".strip()
        result = self.provider.generate_text(prompt, temperature=0.25, num_predict=2500)
        return result.text, result.latency_ms

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
