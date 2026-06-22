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
        }
    )
