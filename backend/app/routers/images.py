import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response

from app.ai_providers.image_worker import DEFAULT_NEGATIVE_PROMPT, ImageWorkerClient, ImageWorkerError
from app.config import Settings, get_settings
from app.jobs import JobStore, get_job_store, now_iso
from app.schemas import ApiEnvelope, ImageJobRequest, ProjectResponse, Scene, StandaloneImageJobRequest
from app.storage import ProjectStorage

router = APIRouter(tags=["images"])

DEFAULT_WIDTH = 768
DEFAULT_HEIGHT = 768
POLL_INTERVAL_SECONDS = 1.5
POLL_MAX_ATTEMPTS = 80  # ~2 minutes per scene, matches the TTS generate-all budget

# Phase 2.3 continuity foundation: each preset is a prompt prefix only (Tier 1,
# prompt-only continuity per docs/IMAGE_CONTINUITY_STRATEGY.md) -- it does not
# pin faces/objects across scenes, it only keeps the rendering style consistent.
STYLE_PRESETS: dict[str, str] = {
    "cinematic_realistic": "cinematic realistic photography, natural lighting, highly detailed",
    "warm_storybook": "warm storybook illustration, soft colors, gentle lighting, hand-drawn feel",
    "anime_cartoon": "anime cartoon style, vibrant colors, clean lineart",
    "military_documentary": "military documentary photo style, gritty realism, muted tones",
    "horror_suspense": "horror suspense atmosphere, dark moody lighting, high contrast, unsettling",
    "marketing_poster": "marketing poster style, bold composition, vibrant colors, polished",
}

# Manual-QA fix pack (2026-06-25, Issue 4): a fixed continuity instruction
# appended to every scene prompt, on top of the existing bibles. This is
# still prompt-only (Tier 1) -- each scene is still a fully independent
# generation call with no real cross-scene memory, no IPAdapter/ControlNet/
# reference image. It only biases a single generation to respect whatever
# the character/location/object bibles already say, instead of drifting
# (e.g. the observed bug: a child described as being in the street ending
# up inside a room with no narrative reason). Quality remains CANDIDATE.
CONTINUITY_RULES = (
    "Maintain visual continuity with the rest of this story: keep the same characters "
    "across all scenes; do not change a character's gender, age, clothing, or identity; "
    "preserve the same recurring object if one is mentioned; respect the scene's own "
    "location and the story's location transitions; do not move a character indoors "
    "or to a different location unless this scene's own description says so."
)


def build_scene_image_prompt(project: ProjectResponse, scene: Scene) -> str:
    parts: list[str] = []
    preset_text = STYLE_PRESETS.get(project.style_preset, "")
    if preset_text:
        parts.append(preset_text)
    if project.story_style_bible.strip():
        parts.append(project.story_style_bible.strip())
    parts.append(scene.image_prompt_en.strip())
    if project.character_bible.strip():
        parts.append(f"Characters: {project.character_bible.strip()}")
    if project.location_bible.strip():
        parts.append(f"Location: {project.location_bible.strip()}")
    if project.object_bible.strip():
        parts.append(f"Important objects: {project.object_bible.strip()}")
    parts.append(CONTINUITY_RULES)
    return ", ".join(part for part in parts if part)


def build_negative_prompt(project: ProjectResponse) -> str:
    return project.negative_prompt.strip() or DEFAULT_NEGATIVE_PROMPT


def _generate_and_save_scene_image(
    project_id: str,
    project: ProjectResponse,
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
    if not scene.image_prompt_en.strip():
        raise ImageWorkerError("لا يوجد وصف بصري (image_prompt_en) لهذا المشهد لتوليد صورة منه.")
    prompt = build_scene_image_prompt(project, scene)

    seed = int(time.time())
    job_id = client.create_job(prompt, width, height, seed, negative_prompt=build_negative_prompt(project))
    job = client.get_job(job_id)
    for _ in range(POLL_MAX_ATTEMPTS):
        if job.get("status") in ("done", "failed"):
            break
        time.sleep(POLL_INTERVAL_SECONDS)
        job = client.get_job(job_id)

    if job.get("status") != "done":
        raise ImageWorkerError(job.get("error") or "انتهت مهلة توليد الصورة.")

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


def get_store(settings: Settings = Depends(get_settings)) -> JobStore:
    return get_job_store(settings.data_path)


def _run_generate_all_images_job(
    job_store: JobStore,
    job_id: str,
    project_id: str,
    project: ProjectResponse,
    client: ImageWorkerClient,
    storage: ProjectStorage,
    width: int,
    height: int,
) -> None:
    job_store.update(job_id, status="running", started_at=now_iso())
    try:
        generated: list[str] = []
        failed: list[dict[str, str]] = []
        total = len(project.scenes)
        for index, scene in enumerate(project.scenes, start=1):
            job_store.update(
                job_id,
                current_step=index,
                total_steps=total,
                completed_steps=index - 1,
                message_ar=f"جاري توليد صورة المشهد {index} من {total}...",
            )
            if not scene.image_prompt_en.strip():
                failed.append({"scene_id": scene.scene_id, "error": "Empty image_prompt_en."})
                continue
            try:
                _generate_and_save_scene_image(project_id, project, scene, client, storage, width, height)
                generated.append(scene.scene_id)
            except ImageWorkerError as exc:
                failed.append({"scene_id": scene.scene_id, "error": str(exc)})
        job_store.update(
            job_id,
            status="done",
            current_step=total,
            completed_steps=total,
            finished_at=now_iso(),
            message_ar=f"تم توليد {len(generated)} من {total}.",
            affected_scene_ids=generated,
            result_summary={"generated": generated, "failed": failed, "total_scenes": total},
        )
    except Exception:
        job_store.update(
            job_id,
            status="failed",
            finished_at=now_iso(),
            safe_error_ar="حدث خطأ غير متوقع أثناء توليد الصور.",
            message_ar="فشل توليد الصور.",
        )


@router.get("/api/images/style-presets", response_model=ApiEnvelope)
def list_style_presets() -> ApiEnvelope:
    presets = [{"key": key, "prompt_prefix": value} for key, value in STYLE_PRESETS.items()]
    return ApiEnvelope(data={"presets": presets})


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
        prompt = prompt or build_scene_image_prompt(project, scene)
    if not prompt:
        raise HTTPException(status_code=422, detail="No image prompt available for this job.")

    try:
        job_id = client.create_job(
            prompt,
            request.width or DEFAULT_WIDTH,
            request.height or DEFAULT_HEIGHT,
            request.seed if request.seed is not None else int(time.time()),
            negative_prompt=build_negative_prompt(project),
        )
    except ImageWorkerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ApiEnvelope(
        data={"job_id": job_id, "status": "queued", "scene_id": request.scene_id, "prompt": prompt},
        meta={"provider": "image-worker"},
    )


@router.get("/api/projects/{project_id}/images/scenes/{scene_id}/prompt-preview", response_model=ApiEnvelope)
def preview_scene_image_prompt(
    project_id: str,
    scene_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    """Milestone F: show the exact assembled prompt (style preset + story/
    character/location/object bibles + continuity rules) before spending an
    AI Server job on it -- read-only, no image worker call."""
    try:
        project = storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    scene = next((s for s in project.scenes if s.scene_id == scene_id), None)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found in project.")

    return ApiEnvelope(
        data={
            "scene_id": scene_id,
            "prompt": build_scene_image_prompt(project, scene),
            "negative_prompt": build_negative_prompt(project),
        }
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
        _generate_and_save_scene_image(project_id, project, scene, client, storage, DEFAULT_WIDTH, DEFAULT_HEIGHT)
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
            _generate_and_save_scene_image(
                project_id, project, scene, client, storage, DEFAULT_WIDTH, DEFAULT_HEIGHT
            )
            generated.append(scene.scene_id)
        except ImageWorkerError as exc:
            failed.append({"scene_id": scene.scene_id, "error": str(exc)})

    return ApiEnvelope(
        data={"generated": generated, "failed": failed, "total_scenes": len(project.scenes)},
        meta={"provider": "image-worker"},
    )


@router.post("/api/projects/{project_id}/images/generate-all/jobs", response_model=ApiEnvelope)
def generate_all_scene_images_job(
    project_id: str,
    background_tasks: BackgroundTasks,
    client: ImageWorkerClient = Depends(get_image_client),
    storage: ProjectStorage = Depends(get_storage),
    store: JobStore = Depends(get_store),
) -> ApiEnvelope:
    """Job-based variant of /images/generate-all -- returns a job_id immediately
    instead of blocking the request for the whole sequential generation run
    (one job per scene, polled via GET /api/jobs/{job_id})."""
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="Image service is not configured.")

    try:
        project = storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not project.scenes:
        raise HTTPException(status_code=422, detail="Project has no scenes to illustrate.")

    job = store.create(
        project_id,
        "images_generate_all",
        total_steps=len(project.scenes),
        message_ar="في قائمة الانتظار...",
    )
    background_tasks.add_task(
        _run_generate_all_images_job,
        store,
        job.job_id,
        project_id,
        project,
        client,
        storage,
        DEFAULT_WIDTH,
        DEFAULT_HEIGHT,
    )
    return ApiEnvelope(data=job.to_dict(), meta={"provider": "image-worker"})


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


@router.post("/api/images/standalone/jobs", response_model=ApiEnvelope)
def create_standalone_image_job(
    request: StandaloneImageJobRequest,
    client: ImageWorkerClient = Depends(get_image_client),
) -> ApiEnvelope:
    """Milestone G -- Simple Image Studio: a single prompt produces one image,
    deliberately separate from the story/scene pipeline (no scene_id, no
    character/location/object bibles, no continuity rules mixed in). Polling
    and download reuse the existing /api/images/jobs/{job_id} endpoints
    below, which were already project-agnostic."""
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="Image service is not configured.")

    parts = []
    if request.style_preset:
        preset_text = STYLE_PRESETS.get(request.style_preset, "")
        if preset_text:
            parts.append(preset_text)
    parts.append(request.prompt)
    prompt = ", ".join(parts)

    try:
        job_id = client.create_job(
            prompt,
            request.width or DEFAULT_WIDTH,
            request.height or DEFAULT_HEIGHT,
            request.seed if request.seed is not None else int(time.time()),
            negative_prompt=request.negative_prompt or DEFAULT_NEGATIVE_PROMPT,
        )
    except ImageWorkerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ApiEnvelope(
        data={"job_id": job_id, "status": "queued", "prompt": prompt},
        meta={"provider": "image-worker", "studio": "standalone"},
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
