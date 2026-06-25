import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response

from app.ai_providers.tts_worker import TtsWorkerClient, TtsWorkerError
from app.config import Settings, get_settings
from app.jobs import JobStore, get_job_store, now_iso
from app.schemas import ApiEnvelope, ProjectResponse, TtsJobRequest
from app.storage import ProjectStorage

router = APIRouter(tags=["tts"])

POLL_INTERVAL_SECONDS = 1.5
POLL_MAX_ATTEMPTS = 80  # ~2 minutes per scene at the interval above

# The deployed worker (deploy/ai-server/tts-worker) has no voice-listing endpoint
# and currently only runs Piper with this one voice. Reflect that honestly instead
# of inventing options the worker doesn't actually support.
KNOWN_VOICES = [
    {
        "voice_id": "ar_JO-kareem-medium",
        "label": "Arabic Kareem",
        "language": "ar",
        "engine": "piper",
        "default": True,
    }
]
KNOWN_LANGUAGES = [{"language": "ar", "label": "العربية", "default": True}]


def get_tts_client(settings: Settings = Depends(get_settings)) -> TtsWorkerClient:
    return TtsWorkerClient(settings)


def get_storage(settings: Settings = Depends(get_settings)) -> ProjectStorage:
    return ProjectStorage(settings)


def get_store(settings: Settings = Depends(get_settings)) -> JobStore:
    return get_job_store(settings.data_path)


def _run_generate_all_audio_job(
    job_store: JobStore,
    job_id: str,
    project_id: str,
    project: ProjectResponse,
    client: TtsWorkerClient,
    storage: ProjectStorage,
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
                message_ar=f"جاري توليد صوت المشهد {index} من {total}...",
            )
            if not scene.narration_ar.strip():
                failed.append({"scene_id": scene.scene_id, "error": "Empty narration."})
                continue
            try:
                job = client.create_job(
                    {"text": scene.narration_ar, "voice_id": None, "speed": None, "format": "wav"}
                )
                tts_job_id = job["job_id"]
                for _ in range(POLL_MAX_ATTEMPTS):
                    if job.get("status") in ("done", "failed"):
                        break
                    time.sleep(POLL_INTERVAL_SECONDS)
                    job = client.get_job(tts_job_id)
                if job.get("status") != "done":
                    failed.append({"scene_id": scene.scene_id, "error": job.get("error") or "Timed out."})
                    continue
                audio_bytes, _ = client.download_file(tts_job_id, "wav")
                storage.save_scene_audio(project_id, scene.scene_id, audio_bytes, "wav")
                generated.append(scene.scene_id)
            except TtsWorkerError as exc:
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
            safe_error_ar="حدث خطأ غير متوقع أثناء توليد الصوت.",
            message_ar="فشل توليد الصوت.",
        )


def _sanitize_job(job: dict) -> dict:
    """Strip the worker's internal container filesystem paths before returning to the browser."""
    files = job.get("files")
    if isinstance(files, list):
        job = {**job, "files": [{k: v for k, v in f.items() if k != "path"} for f in files]}
    return job


@router.get("/api/tts/health", response_model=ApiEnvelope)
def tts_health(client: TtsWorkerClient = Depends(get_tts_client)) -> ApiEnvelope:
    data = client.health()
    errors = []
    if data["configured"] and data.get("remote_ok") is False:
        errors.append("TTS worker is not reachable.")
    return ApiEnvelope(data=data, meta={"provider": "tts-worker"}, errors=errors)


@router.get("/api/tts/voices", response_model=ApiEnvelope)
def list_tts_voices() -> ApiEnvelope:
    return ApiEnvelope(
        data={"voices": KNOWN_VOICES, "languages": KNOWN_LANGUAGES},
        meta={"provider": "tts-worker"},
    )


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

    return ApiEnvelope(data=_sanitize_job(result), meta={"provider": "tts-worker"})


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


@router.post("/api/projects/{project_id}/tts/generate-all/jobs", response_model=ApiEnvelope)
def generate_all_scene_audio_job(
    project_id: str,
    background_tasks: BackgroundTasks,
    client: TtsWorkerClient = Depends(get_tts_client),
    storage: ProjectStorage = Depends(get_storage),
    store: JobStore = Depends(get_store),
) -> ApiEnvelope:
    """Job-based variant of /tts/generate-all -- returns a job_id immediately
    instead of blocking the request for the whole sequential narration run."""
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="TTS service is not configured.")

    try:
        project = storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not project.scenes:
        raise HTTPException(status_code=422, detail="Project has no scenes to narrate.")

    job = store.create(
        project_id,
        "audio_generate_all",
        total_steps=len(project.scenes),
        message_ar="في قائمة الانتظار...",
    )
    background_tasks.add_task(_run_generate_all_audio_job, store, job.job_id, project_id, project, client, storage)
    return ApiEnvelope(data=job.to_dict(), meta={"provider": "tts-worker"})


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
    return ApiEnvelope(data=_sanitize_job(result), meta={"provider": "tts-worker"})


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


@router.get("/api/projects/{project_id}/audio", response_model=ApiEnvelope)
def get_project_audio(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    try:
        project = storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    scenes_with_audio_ids = {scene.scene_id for scene in storage.get_scenes_with_audio(project)}
    scenes = []
    wav_scene_count = 0
    for scene in project.scenes:
        has_audio = scene.scene_id in scenes_with_audio_ids
        if has_audio and scene.audio_format == "wav":
            wav_scene_count += 1
        scenes.append(
            {
                "scene_id": scene.scene_id,
                "has_audio": has_audio,
                "audio_format": scene.audio_format if has_audio else None,
                "audio_bytes": scene.audio_bytes if has_audio else None,
                "audio_generated_at": scene.audio_generated_at.isoformat()
                if has_audio and scene.audio_generated_at
                else None,
                "url": f"/api/projects/{project_id}/audio/{scene.scene_id}" if has_audio else None,
            }
        )

    final_story_available = wav_scene_count > 1
    return ApiEnvelope(
        data={
            "project_id": project_id,
            "scenes": scenes,
            "final_story": {
                "has_audio": final_story_available,
                "url": f"/api/projects/{project_id}/audio/final_story.wav"
                if final_story_available
                else None,
            },
        }
    )


@router.get("/api/projects/{project_id}/audio/final_story.wav")
def get_final_story_audio(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> Response:
    try:
        storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    audio_bytes = storage.build_final_story_wav(project_id)
    if audio_bytes is None:
        raise HTTPException(status_code=404, detail="Final story audio not available.")
    return Response(content=audio_bytes, media_type="audio/wav")


@router.get("/api/projects/{project_id}/audio/{scene_id}")
def get_scene_audio(
    project_id: str,
    scene_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> Response:
    try:
        storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    path = storage.get_scene_audio_path(project_id, scene_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Scene audio not found.")
    media_type = "audio/wav" if path.suffix == ".wav" else "audio/mpeg"
    return Response(content=path.read_bytes(), media_type=media_type)
