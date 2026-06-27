from fastapi import APIRouter

from app.config import get_settings
from app.schemas import ApiEnvelope

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config", response_model=ApiEnvelope)
def config() -> ApiEnvelope:
    settings = get_settings()
    return ApiEnvelope(
        data={
            "provider": "ollama",
            "model": settings.ollama_model,
            "ollama_configured": settings.ollama_configured,
            "long_story_chunk_chars": settings.long_story_chunk_chars,
            "story_job_threshold_chars": settings.story_job_threshold_chars,
            "long_story_max_total_seconds": settings.long_story_max_total_seconds,
            "ollama_timeout_seconds": settings.ollama_timeout_seconds,
        }
    )
