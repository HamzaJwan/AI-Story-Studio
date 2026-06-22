from fastapi import APIRouter

from app.config import get_settings
from app.schemas import ApiEnvelope

router = APIRouter()


@router.get("/health", response_model=ApiEnvelope)
def health() -> ApiEnvelope:
    settings = get_settings()
    return ApiEnvelope(
        data={
            "status": "ok",
            "app": settings.app_name,
            "phase": settings.app_phase,
        }
    )
