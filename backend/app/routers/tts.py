import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.ai_providers.tts_worker import TtsWorkerClient, TtsWorkerError
from app.config import Settings, get_settings
from app.schemas import ApiEnvelope, TtsJobRequest
from app.storage import ProjectStorage

router = APIRouter(tags=["tts"])

POLL_INTERVAL_SECONDS = 1.5
POLL_MAX_ATTEMPTS = 80  # ~2 minutes per scene at the interval above


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
        scene = next((s for s in project.scenes if s.scene_id == request.scene_id), None)
        if scene is None:
            raise HTTPException(status_code=404, detail="Scene not found in project.")
        text = scene.narration_ar
    else:
        if not project.scenes:
            raise HTTPException(status_code=422, detail="Project has no scenes to narrate.")
        text = "\n".join(scene.narration_ar for scene in project.scenes)

    if not text.strip():
        raise HTTPException(status_code=422, detail="Scene narration is empty.")

    payload = {
        "project_id": project.project_id,
        "mode": request.mode,
        "scene_id": request.scene_id,
        "text": text,
        "voice_id": request.voice_id,
        "speed": request.speed,
        "format": request.format,
    }
    try:
        result = client.create_job(payload)
    except TtsWorkerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ApiEnvelope(data=result, meta={"provider": "tts-worker"})


@router.post("/api/projects/{project_id}/tts/generate-all", response_model=ApiEnvelope)
def generate_all_scene_audio(
    project_id: str,
    client: TtsWorkerClient = Depends(get_tts_client),
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="TTS service is not configured.")

    try:
        project = storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not project.scenes:
        raise HTTPException(status_code=422, detail="Project has no scenes to narrate.")

    generated: list[str] = []
    failed: list[dict[str, str]] = []

    for scene in project.scenes:
        if not scene.narration_ar.strip():
            failed.append({"scene_id": scene.scene_id, "error": "Empty narration."})
            continue
        try:
            job = client.create_job(
                {"text": scene.narration_ar, "voice_id": None, "speed": None, "format": "wav"}
            )
            job_id = job["job_id"]
            for _ in range(POLL_MAX_ATTEMPTS):
                if job.get("status") in ("done", "failed"):
                    break
                time.sleep(POLL_INTERVAL_SECONDS)
                job = client.get_job(job_id)
            if job.get("status") != "done":
                failed.append({"scene_id": scene.scene_id, "error": job.get("error") or "Timed out."})
                continue
            audio_bytes, _ = client.download_file(job_id, "wav")
            storage.save_scene_audio(project_id, scene.scene_id, audio_bytes, "wav")
            generated.append(scene.scene_id)
        except TtsWorkerError as exc:
            failed.append({"scene_id": scene.scene_id, "error": str(exc)})

    return ApiEnvelope(
        data={"generated": generated, "failed": failed, "total_scenes": len(project.scenes)},
        meta={"provider": "tts-worker"},
    )


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


@router.get("/api/tts/jobs/{job_id}/download/{fmt}")
def download_tts_job_file(
    job_id: str,
    fmt: str,
    client: TtsWorkerClient = Depends(get_tts_client),
) -> Response:
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="TTS service is not configured.")
    try:
        content, content_type = client.download_file(job_id, fmt)
    except TtsWorkerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(content=content, media_type=content_type)
