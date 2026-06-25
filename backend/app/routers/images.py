import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.ai_providers.image_worker import ImageWorkerClient, ImageWorkerError
from app.config import Settings, get_settings
from app.schemas import ApiEnvelope, ImageJobRequest
from app.storage import ProjectStorage

router = APIRouter(tags=["images"])

DEFAULT_WIDTH = 768
DEFAULT_HEIGHT = 768


def get_image_client(settings: Settings = Depends(get_settings)) -> ImageWorkerClient:
    return ImageWorkerClient(settings)


def get_storage(settings: Settings = Depends(get_settings)) -> ProjectStorage:
    return ProjectStorage(settings)


@router.get("/api/images/health", response_model=ApiEnvelope)
def images_health(client: ImageWorkerClient = Depends(get_image_client)) -> ApiEnvelope:
    data = client.health()
    errors = []
    if data["configured"] and data.get("remote_ok") is False:
        errors.append("Image worker is not reachable.")
    return ApiEnvelope(data=data, meta={"provider": "image-worker"}, errors=errors)


@router.post("/api/projects/{project_id}/images/jobs", response_model=ApiEnvelope)
def create_image_job(
    project_id: str,
    request: ImageJobRequest,
    client: ImageWorkerClient = Depends(get_image_client),
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="Image service is not configured.")

    try:
        project = storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    prompt = (request.prompt or "").strip()
    if request.scene_id:
        scene = next((s for s in project.scenes if s.scene_id == request.scene_id), None)
        if scene is None:
            raise HTTPException(status_code=404, detail="Scene not found in project.")
        prompt = prompt or scene.image_prompt_en.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="No image prompt available for this job.")

    try:
        job_id = client.create_job(
            prompt,
            request.width or DEFAULT_WIDTH,
            request.height or DEFAULT_HEIGHT,
            request.seed if request.seed is not None else int(time.time()),
        )
    except ImageWorkerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ApiEnvelope(
        data={"job_id": job_id, "status": "queued", "scene_id": request.scene_id, "prompt": prompt},
        meta={"provider": "image-worker"},
    )


@router.get("/api/images/jobs/{job_id}", response_model=ApiEnvelope)
def get_image_job(job_id: str, client: ImageWorkerClient = Depends(get_image_client)) -> ApiEnvelope:
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="Image service is not configured.")
    try:
        result = client.get_job(job_id)
    except ImageWorkerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ApiEnvelope(data=result, meta={"provider": "image-worker"})


@router.get("/api/images/jobs/{job_id}/download")
def download_image_job_file(
    job_id: str,
    client: ImageWorkerClient = Depends(get_image_client),
) -> Response:
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="Image service is not configured.")
    try:
        job = client.get_job(job_id)
    except ImageWorkerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if job["status"] != "done" or not job["files"]:
        raise HTTPException(status_code=404, detail="Image not ready or not found.")
    file_info = job["files"][0]
    try:
        content, content_type = client.download_file(
            file_info["filename"], file_info["subfolder"], file_info["type"]
        )
    except ImageWorkerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(content=content, media_type=content_type)
