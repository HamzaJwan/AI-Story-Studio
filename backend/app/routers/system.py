"""Milestone I -- Model/Engine Status Dashboard.

Aggregates the existing per-provider health checks (Ollama/TTS/image worker)
plus local ffmpeg availability into one read-only status payload. Every
field here was already safe to expose before this router existed (each
provider's own `health()` strips URLs down to booleans/latency) -- this
endpoint only combines them so the frontend can show one dashboard instead
of three separate panels. No IPs, no `.env` values, no container paths.
"""

from __future__ import annotations

import shutil

from fastapi import APIRouter, Depends

from app.ai_providers.image_worker import ImageWorkerClient
from app.ai_providers.ollama import OllamaProvider
from app.ai_providers.tts_worker import TtsWorkerClient
from app.config import Settings, get_settings
from app.schemas import ApiEnvelope

router = APIRouter(tags=["system"])


@router.get("/api/system/status", response_model=ApiEnvelope)
def system_status(settings: Settings = Depends(get_settings)) -> ApiEnvelope:
    ollama = OllamaProvider(settings).health()
    tts = TtsWorkerClient(settings).health()
    image = ImageWorkerClient(settings).health()
    ffmpeg_available = shutil.which("ffmpeg") is not None

    return ApiEnvelope(
        data={
            "ollama": ollama,
            "tts": tts,
            "image": image,
            "ffmpeg": {"available": ffmpeg_available},
            "benchmark_notes_doc": "docs/IMAGE_QUALITY_APPROVAL_CHECKLIST.md",
        }
    )
