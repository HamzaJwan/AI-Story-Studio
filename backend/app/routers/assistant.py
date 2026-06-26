"""Milestone 13 -- Local Assistant Lab (the safe, simple fallback version).

Per `docs/LOCAL_AI_ASSISTANT_LAB_PLAN.md`, a full chat assistant (RAG, web
search, vision, conversation history) is explicitly deferred to Phase 4.x and
should use Open WebUI rather than a custom build. This module is the smallest
safe slice that's actually useful now: a single-turn, stateless question
about *one project's own data*, answered by the same local Ollama model the
rest of the app already uses. No new service, no DB, no citations claimed
(there is no retrieval step to cite), no conversation memory.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.ai_providers.ollama import OllamaError, OllamaProvider
from app.config import Settings, get_settings
from app.routers.ollama import get_provider
from app.schemas import AssistantAskRequest, ApiEnvelope, ProjectResponse
from app.storage import ProjectStorage

router = APIRouter(tags=["assistant"])

# Keeps the prompt well inside any local model's context window -- this is a
# quick single-turn Q&A, not the long-story-improve path, so it does not need
# chunking; it just needs a bounded, cheap prompt.
MAX_CONTEXT_CHARS = 4000
MAX_SCENES_IN_CONTEXT = 12


def get_storage(settings: Settings = Depends(get_settings)) -> ProjectStorage:
    return ProjectStorage(settings)


def _build_project_context(project: ProjectResponse) -> str:
    parts: list[str] = [f"عنوان المشروع: {project.title}"]
    story_text = (project.improved_story or project.original_story or "").strip()
    if story_text:
        parts.append(f"نص القصة (قد يكون مقتطفاً): {story_text[:MAX_CONTEXT_CHARS]}")
    for scene in project.scenes[:MAX_SCENES_IN_CONTEXT]:
        narration = scene.narration_ar.strip()[:300]
        parts.append(f"مشهد {scene.scene_id} - {scene.title_ar}: {narration}")
    return "\n".join(parts)


def _build_prompt(project: ProjectResponse, question: str) -> str:
    context = _build_project_context(project)
    return f"""
أنت مساعد يجيب فقط بالاستناد إلى معلومات المشروع أدناه. إذا لم تجد إجابة واضحة
في هذه المعلومات، قل بوضوح أنك لا تعرف، ولا تخترع أي تفاصيل غير موجودة فيها.
أجب بالعربية وبإيجاز.

معلومات المشروع:
{context}

سؤال المستخدم: {question}
""".strip()


@router.post("/api/projects/{project_id}/assistant/ask", response_model=ApiEnvelope)
def ask_about_project(
    project_id: str,
    request: AssistantAskRequest,
    provider: OllamaProvider = Depends(get_provider),
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    try:
        project = storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        result = provider.generate_text(
            _build_prompt(project, request.question),
            temperature=0.2,
            num_predict=600,
        )
    except OllamaError as exc:
        return ApiEnvelope(data={"answer": ""}, meta={"provider": "ollama"}, errors=[str(exc)])

    return ApiEnvelope(
        data={"answer": result.text},
        meta={
            "provider": "ollama",
            "model": result.model,
            "latency_ms": result.latency_ms,
            "limitations": [
                "إجابة من Ollama مباشرة بدون RAG حقيقي أو بحث إنترنت -- قد تكون غير دقيقة، راجعها دائماً.",
            ],
        },
    )
