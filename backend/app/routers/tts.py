from fastapi import APIRouter, Depends, HTTPException

from app.ai_providers.tts_worker import TtsWorkerClient, TtsWorkerError
from app.config import Settings, get_settings
from app.schemas import ApiEnvelope, TtsJobRequest
from app.storage import ProjectStorage

router = APIRouter(tags=["tts"])


def get_tts_client(settings: Settings = Depends(get_settings)) -> TtsWorkerClient:
    return TtsWorkerClient(settings)


def get_storage(settings: Settings = Depends(get_settings)) -> ProjectStorage:
    return ProjectStorage(settings)


@router.get("/api/tts/health", response_model=ApiEnvelope)
def tts_health(client: TtsWorkerClient = Depends(get_tts_client)) -> ApiEnvelope:
    data = client.health()
    errors = []
    if data["configured"] and data.get("remote_ok") is False:
        errors.append("TTS worker is not reachable.")
    return ApiEnvelope(data=data, meta={"provider": "tts-worker"}, errors=errors)


@router.post("/api/projects/{project_id}/tts/jobs", response_model=ApiEnvelope)
def create_tts_job(
    project_id: str,
    request: TtsJobRequest,
    client: TtsWorkerClient = Depends(get_tts_client),
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="TTS service is not configured.")

    try:
        project = storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if request.mode == "scene":
        if not request.scene_id:
            raise HTTPException(
                status_code=422, detail="scene_id is required when mode is 'scene'."
            )
        if not any(scene.scene_id == request.scene_id for scene in project.scenes):
            raise HTTPException(status_code=404, detail="Scene not found in project.")

    payload = {
        "project_id": project.project_id,
        "mode": request.mode,
        "scene_id": request.scene_id,
        "voice_id": request.voice_id,
        "speed": request.speed,
        "format": request.format,
    }
    try:
        result = client.create_job(payload)
    except TtsWorkerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ApiEnvelope(data=result, meta={"provider": "tts-worker"})


@router.get("/api/tts/jobs/{job_id}", response_model=ApiEnvelope)
def get_tts_job(
    job_id: str,
    client: TtsWorkerClient = Depends(get_tts_client),
) -> ApiEnvelope:
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="TTS service is not configured.")
    try:
        result = client.get_job(job_id)
    except TtsWorkerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ApiEnvelope(data=result, meta={"provider": "tts-worker"})
