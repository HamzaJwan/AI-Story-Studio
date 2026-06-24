from fastapi import APIRouter, Depends

from app.ai_providers.ollama import OllamaError, OllamaProvider
from app.config import Settings, get_settings
from app.routers.ollama import get_provider
from app.schemas import ApiEnvelope, ImproveStoryRequest, SplitScenesRequest
from app.storage import ProjectStorage
from app.story_engine.engine import StoryEngine, StoryEngineError

router = APIRouter(prefix="/api", tags=["story"])


def get_storage(settings: Settings = Depends(get_settings)) -> ProjectStorage:
    return ProjectStorage(settings)


@router.post("/story/improve", response_model=ApiEnvelope)
@router.post("/story/improve-narration", response_model=ApiEnvelope)
def improve_story(
    request: ImproveStoryRequest,
    provider: OllamaProvider = Depends(get_provider),
) -> ApiEnvelope:
    try:
        engine = StoryEngine(provider)
        improved_text, latency_ms = engine.improve_narration_script(
            story_text=request.story_text,
            tone=request.tone,
            language=request.language,
        )
        return ApiEnvelope(
            data={"improved_text": improved_text},
            meta={
                "provider": "ollama",
                "model": provider.model,
                "latency_ms": latency_ms,
                "limitations": ["AI output requires human review"],
            },
        )
    except OllamaError as exc:
        return ApiEnvelope(
            data={"improved_text": ""},
            meta={"provider": "ollama", "model": provider.model},
            errors=[str(exc)],
        )


@router.post("/story/split-scenes", response_model=ApiEnvelope)
def split_scenes(
    request: SplitScenesRequest,
    provider: OllamaProvider = Depends(get_provider),
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    try:
        engine = StoryEngine(provider)
        split_data, latency_ms = engine.split_into_scenes(request)
        saved_data = storage.save_story_project(
            story_text=request.story_text,
            split_data=split_data,
            provider="ollama",
            model=provider.model,
        )
        return ApiEnvelope(
            data=saved_data.model_dump(),
            meta={
                "provider": "ollama",
                "model": provider.model,
                "latency_ms": latency_ms,
                "limitations": ["AI output requires human review"],
            },
        )
    except (OllamaError, StoryEngineError) as exc:
        return ApiEnvelope(
            data={"project_id": None, "story_title": request.title, "scenes": []},
            meta={"provider": "ollama", "model": provider.model},
            errors=[str(exc)],
        )
