import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.ai_providers.image_worker import ImageWorkerClient, ImageWorkerError
from app.config import Settings, get_settings
from app.schemas import ApiEnvelope, ImageJobRequest, Scene
from app.storage import ProjectStorage

router = APIRouter(tags=["images"])

DEFAULT_WIDTH = 768
DEFAULT_HEIGHT = 768
POLL_INTERVAL_SECONDS = 1.5
POLL_MAX_ATTEMPTS = 80  # ~2 minutes per scene, matches the TTS generate-all budget


def _generate_and_save_scene_image(
    project_id: str,
    scene: Scene,
    client: ImageWorkerClient,
    storage: ProjectStorage,
    width: int,
    height: int,
) -> None:
    """Submit a job for one scene, block until done, download, and persist it.

    Raises ImageWorkerError or TimeoutError on failure -- callers decide how to
    record that (single 502 vs. a per-scene entry in a generate-all summary).
    """
    prompt = scene.image_prompt_en.strip()
    if not prompt:
        raise ImageWorkerError("Scene has no image_prompt_en to generate from.")

    seed = int(time.time())
    job_id = client.create_job(prompt, width, height, seed)
    job = client.get_job(job_id)
    for _ in range(POLL_MAX_ATTEMPTS):
        if job.get("status") in ("done", "failed"):
            break
        time.sleep(POLL_INTERVAL_SECONDS)
        job = client.get_job(job_id)

    if job.get("status") != "done":
        raise ImageWorkerError(job.get("error") or "Image generation timed out.")

    file_info = job["files"][0]
    content, _ = client.download_file(file_info["filename"], file_info["subfolder"], file_info["type"])
    storage.save_scene_image(
        project_id,
        scene.scene_id,
        content,
        "png",
        width,
        height,
        "comfyui-sdxl",
        seed,
        prompt,
    )


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


@router.post("/api/projects/{project_id}/images/scenes/{scene_id}/generate", response_model=ApiEnvelope)
def generate_scene_image(
    project_id: str,
    scene_id: str,
    client: ImageWorkerClient = Depends(get_image_client),
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    """Synchronous, persisted single-scene generation -- powers "generate"/"regenerate"."""
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="Image service is not configured.")

    try:
        project = storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    scene = next((s for s in project.scenes if s.scene_id == scene_id), None)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found in project.")

    try:
        _generate_and_save_scene_image(project_id, scene, client, storage, DEFAULT_WIDTH, DEFAULT_HEIGHT)
    except ImageWorkerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ApiEnvelope(data={"scene_id": scene_id, "status": "done"}, meta={"provider": "image-worker"})


@router.post("/api/projects/{project_id}/images/generate-all", response_model=ApiEnvelope)
def generate_all_scene_images(
    project_id: str,
    client: ImageWorkerClient = Depends(get_image_client),
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="Image service is not configured.")

    try:
        project = storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not project.scenes:
        raise HTTPException(status_code=422, detail="Project has no scenes to illustrate.")

    generated: list[str] = []
    failed: list[dict[str, str]] = []

    # Sequential on purpose: the AI Server's VRAM margin is tight (~812 MiB free at
    # peak per docs/IMAGE_QUALITY_APPROVAL_CHECKLIST.md) -- parallel jobs risk OOM.
    for scene in project.scenes:
        if not scene.image_prompt_en.strip():
            failed.append({"scene_id": scene.scene_id, "error": "Empty image_prompt_en."})
            continue
        try:
            _generate_and_save_scene_image(project_id, scene, client, storage, DEFAULT_WIDTH, DEFAULT_HEIGHT)
            generated.append(scene.scene_id)
        except ImageWorkerError as exc:
            failed.append({"scene_id": scene.scene_id, "error": str(exc)})

    return ApiEnvelope(
        data={"generated": generated, "failed": failed, "total_scenes": len(project.scenes)},
        meta={"provider": "image-worker"},
    )


@router.get("/api/projects/{project_id}/images", response_model=ApiEnvelope)
def get_project_images(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    try:
        project = storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    scenes_with_images_ids = {scene.scene_id for scene in storage.get_scenes_with_images(project)}
    scenes = []
    for scene in project.scenes:
        has_image = scene.scene_id in scenes_with_images_ids
        scenes.append(
            {
                "scene_id": scene.scene_id,
                "has_image": has_image,
                "image_format": scene.image_format if has_image else None,
                "image_bytes": scene.image_bytes if has_image else None,
                "image_width": scene.image_width if has_image else None,
                "image_height": scene.image_height if has_image else None,
                "image_generated_at": scene.image_generated_at.isoformat()
                if has_image and scene.image_generated_at
                else None,
                "url": f"/api/projects/{project_id}/images/{scene.scene_id}" if has_image else None,
            }
        )

    return ApiEnvelope(data={"project_id": project_id, "scenes": scenes})


@router.get("/api/projects/{project_id}/images/{scene_id}")
def get_scene_image(
    project_id: str,
    scene_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> Response:
    try:
        storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    path = storage.get_scene_image_path(project_id, scene_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Scene image not found.")
    return Response(content=path.read_bytes(), media_type="image/png")


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
