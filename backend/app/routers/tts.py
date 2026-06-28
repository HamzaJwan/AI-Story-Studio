import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response

from app.ai_providers.tts_worker import TtsWorkerClient, TtsWorkerError
from app.config import Settings, get_settings
from app.jobs import JobStore, get_job_store, now_iso
from app.schemas import ApiEnvelope, ProjectResponse, Scene, TtsJobRequest
from app.storage import ProjectStorage

router = APIRouter(tags=["tts"])

POLL_INTERVAL_SECONDS = 1.5
POLL_MAX_ATTEMPTS = 80  # ~2 minutes per scene at the interval above

KNOWN_LANGUAGES = [{"language": "ar", "label": "العربية", "default": True}]

# Voice Expansion Lab (2026-06-28): every voice the worker could in principle
# serve, *not* "every voice the UI may show". Availability is decided live in
# get_voice_catalog() against the worker's real /health response, never
# assumed -- see docs/DECISION_LOG.md for why no second Arabic voice is in
# this registry yet:
#   - Piper's own official voice set (rhasspy/piper-voices) has exactly one
#     Arabic speaker ("kareem", ar_JO) in two quality tiers of the SAME
#     speaker -- not a second voice or a female voice.
#   - The AllTalk service reachable on the AI Server exposes several
#     explicitly celebrity-named reference samples (forbidden outright) and
#     several generically-named ones ("arabic_male.wav", "female_01.wav", ...)
#     with no documented consent/provenance -- AllTalk is voice CLONING by
#     design, so every one of those stays Deferred per the safety rules until
#     Hamza supplies his own licensed reference recording.
#   - SILMA is explicitly blocked on this deployment (stalled model download,
#     see worker_app/jobs.py's _run_piper() note).
#   - A community Hugging Face Arabic-Emirati female Piper voice exists, but
#     its model card discloses no consent/provenance for the source speaker,
#     so it cannot pass the "licensed and safe" bar either.
# When a second voice clears safety review, add its registry entry here --
# the catalog/UI/generation plumbing below already supports more than one.
VOICE_REGISTRY = [
    {
        "voice_id": "ar_JO-kareem-medium",
        "display_name_ar": "كريم (عربي - رجل)",
        "gender": "male",
        "language": "ar",
        "engine": "piper",
        "quality_label": "medium",
        "experimental": False,
        "default": True,
        "notes_ar": "صوت Piper مجتمعي مرخّص (MIT)، وليس صوت شخص حقيقي أو مشهور.",
    }
]
DEFAULT_VOICE_ID = next(v["voice_id"] for v in VOICE_REGISTRY if v.get("default"))


def get_voice_catalog(client: TtsWorkerClient) -> list[dict]:
    """Real discovery, not a static guess: a registry voice is only reported
    `available: true` if the worker is actually reachable right now AND is
    actually running the engine that voice needs. The worker has no
    voice-listing endpoint of its own, so this is the safe adapter the task
    calls for -- it never claims a voice works without checking."""
    health = client.health()
    remote_engine = health.get("remote_engine") if health.get("remote_ok") else None
    catalog = []
    for voice in VOICE_REGISTRY:
        available = bool(client.is_configured() and remote_engine == voice["engine"])
        entry = dict(voice)
        entry["available"] = available
        if not available:
            entry["notes_ar"] = (
                f"{voice['notes_ar']} غير متاح حالياً -- تعذر التأكد أن محرك "
                f"{voice['engine']} يعمل على خدمة الصوت الآن."
            )
        catalog.append(entry)
    return catalog


def resolve_voice_id(catalog: list[dict], requested_voice_id: str | None) -> tuple[str | None, str | None]:
    """Returns (resolved_voice_id, error_message_ar). Never silently swaps a
    user's explicit voice choice for a different one -- if they asked for a
    voice that isn't in the catalog or isn't available, that's a failure to
    report, not something to paper over with the default voice."""
    if requested_voice_id is None:
        default = next((v for v in catalog if v["voice_id"] == DEFAULT_VOICE_ID), None)
        if default is None or not default["available"]:
            return None, "الصوت الافتراضي غير متاح حالياً."
        return DEFAULT_VOICE_ID, None
    match = next((v for v in catalog if v["voice_id"] == requested_voice_id), None)
    if match is None:
        return None, "الصوت المطلوب غير معروف."
    if not match["available"]:
        return None, "الصوت المطلوب غير متاح حالياً."
    return requested_voice_id, None


def get_tts_client(settings: Settings = Depends(get_settings)) -> TtsWorkerClient:
    return TtsWorkerClient(settings)


def get_storage(settings: Settings = Depends(get_settings)) -> ProjectStorage:
    return ProjectStorage(settings)


def get_store(settings: Settings = Depends(get_settings)) -> JobStore:
    return get_job_store(settings.data_path)


def _generate_and_persist_scene_audio(
    client: TtsWorkerClient,
    storage: ProjectStorage,
    project_id: str,
    scene: Scene,
    voice_id: str | None = None,
) -> tuple[bool, str | None]:
    """Generate audio for one scene via the worker and persist it to disk +
    project metadata. Shared by the single-scene endpoint, sync generate-all,
    and the job-based generate-all -- one save path, not three (manual QA fix
    pack, 2026-06-27: the single-scene path used to call the worker but never
    save, which is exactly why scene-1 audio appeared to "disappear" after a
    reload -- it was never persisted in the first place).

    `voice_id` is resolved against the live voice catalog (Voice Expansion
    Lab, 2026-06-28) -- if the caller asked for a specific voice and it isn't
    actually available right now, this fails honestly instead of silently
    falling back to a different voice the user didn't choose.

    Returns (success, error_message_ar_or_none). Generation failures and
    save failures are distinguished so the caller can tell the user the
    honest difference between "couldn't generate" and "generated but
    couldn't save into the project."
    """
    if not scene.narration_ar.strip():
        return False, "نص الراوي لهذا المشهد فارغ."

    catalog = get_voice_catalog(client)
    resolved_voice_id, voice_error = resolve_voice_id(catalog, voice_id)
    if voice_error is not None:
        return False, voice_error
    voice_entry = next(v for v in catalog if v["voice_id"] == resolved_voice_id)

    try:
        job = client.create_job(
            {"text": scene.narration_ar, "voice_id": resolved_voice_id, "speed": None, "format": "wav"}
        )
        job_id = job["job_id"]
        for _ in range(POLL_MAX_ATTEMPTS):
            if job.get("status") in ("done", "failed"):
                break
            time.sleep(POLL_INTERVAL_SECONDS)
            job = client.get_job(job_id)
        if job.get("status") != "done":
            return False, job.get("error") or "انتهت مهلة توليد الصوت."
        audio_bytes, _ = client.download_file(job_id, "wav")
    except TtsWorkerError as exc:
        return False, str(exc)

    try:
        storage.save_scene_audio(
            project_id,
            scene.scene_id,
            audio_bytes,
            "wav",
            voice_id=resolved_voice_id,
            engine=voice_entry["engine"],
        )
    except (OSError, FileNotFoundError) as exc:
        return False, f"تم توليد الصوت فعلياً لكن فشل حفظه داخل المشروع: {exc}"
    return True, None


def _run_generate_all_audio_job(
    job_store: JobStore,
    job_id: str,
    project_id: str,
    project: ProjectResponse,
    client: TtsWorkerClient,
    storage: ProjectStorage,
    voice_id: str | None = None,
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
            ok, error = _generate_and_persist_scene_audio(client, storage, project_id, scene, voice_id=voice_id)
            if ok:
                generated.append(scene.scene_id)
            else:
                failed.append({"scene_id": scene.scene_id, "error": error or "Unknown error."})
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
def list_tts_voices(client: TtsWorkerClient = Depends(get_tts_client)) -> ApiEnvelope:
    catalog = get_voice_catalog(client)
    return ApiEnvelope(
        data={
            "voices": catalog,
            "languages": KNOWN_LANGUAGES,
            "default_voice_id": DEFAULT_VOICE_ID,
            "single_voice_available": sum(1 for v in catalog if v["available"]) <= 1,
        },
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
    voice_id: str | None = None,
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
        ok, error = _generate_and_persist_scene_audio(client, storage, project_id, scene, voice_id=voice_id)
        if ok:
            generated.append(scene.scene_id)
        else:
            failed.append({"scene_id": scene.scene_id, "error": error or "Unknown error."})

    return ApiEnvelope(
        data={"generated": generated, "failed": failed, "total_scenes": len(project.scenes)},
        meta={"provider": "tts-worker"},
    )


@router.post("/api/projects/{project_id}/tts/scenes/{scene_id}/generate", response_model=ApiEnvelope)
def generate_scene_audio(
    project_id: str,
    scene_id: str,
    voice_id: str | None = None,
    client: TtsWorkerClient = Depends(get_tts_client),
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    """Synchronous, persisted single-scene audio generation -- powers
    "generate audio for the first/this scene" in the Audio Studio.

    Unlike `POST /api/projects/{project_id}/tts/jobs` (mode=scene), which only
    proxies an ephemeral worker job and was never meant to be the saved-audio
    path, this endpoint always calls the same save logic generate-all uses
    (`_generate_and_persist_scene_audio`), so a single scene's audio survives
    a page reload / project reopen exactly like generate-all's output does.
    """
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="TTS service is not configured.")

    try:
        project = storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    scene = next((s for s in project.scenes if s.scene_id == scene_id), None)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found in project.")

    ok, error = _generate_and_persist_scene_audio(client, storage, project_id, scene, voice_id=voice_id)
    if not ok:
        raise HTTPException(status_code=502, detail=error or "Audio generation failed.")

    return ApiEnvelope(data={"scene_id": scene_id, "status": "done"}, meta={"provider": "tts-worker"})


@router.post("/api/projects/{project_id}/tts/generate-all/jobs", response_model=ApiEnvelope)
def generate_all_scene_audio_job(
    project_id: str,
    background_tasks: BackgroundTasks,
    voice_id: str | None = None,
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
    background_tasks.add_task(
        _run_generate_all_audio_job, store, job.job_id, project_id, project, client, storage, voice_id
    )
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
                "audio_voice_id": scene.audio_voice_id if has_audio else None,
                "audio_engine": scene.audio_engine if has_audio else None,
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
