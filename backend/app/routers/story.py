from fastapi import APIRouter, BackgroundTasks, Depends

from app.ai_providers.ollama import OllamaError, OllamaProvider
from app.config import Settings, get_settings
from app.jobs import JobStore, get_job_store, now_iso
from app.routers.ollama import get_provider
from app.schemas import ApiEnvelope, ImproveStoryRequest, SplitScenesRequest
from app.storage import ProjectStorage
from app.story_engine.engine import StoryEngine, StoryEngineError

router = APIRouter(prefix="/api", tags=["story"])


def get_storage(settings: Settings = Depends(get_settings)) -> ProjectStorage:
    return ProjectStorage(settings)


def get_store(settings: Settings = Depends(get_settings)) -> JobStore:
    return get_job_store(settings.data_path)


def _run_improve_job(
    job_store: JobStore,
    job_id: str,
    provider: OllamaProvider,
    story_text: str,
    tone: str,
    language: str,
    chunk_chars: int,
) -> None:
    job_store.update(job_id, status="running", started_at=now_iso(), message_ar="جاري تحسين القصة...")
    try:
        engine = StoryEngine(provider)

        def on_progress(index: int, total: int) -> None:
            job_store.update(
                job_id,
                current_step=index,
                total_steps=total,
                completed_steps=index - 1,
                message_ar=f"جاري تحسين الجزء {index} من {total}...",
            )

        improved_text, latency_ms, chunk_count = engine.improve_narration_script(
            story_text=story_text,
            tone=tone,
            language=language,
            chunk_chars=chunk_chars,
            on_progress=on_progress,
        )
        job_store.update(
            job_id,
            status="done",
            current_step=chunk_count,
            total_steps=chunk_count,
            completed_steps=chunk_count,
            finished_at=now_iso(),
            message_ar=(
                f"تم تحسين القصة على {chunk_count} أجزاء." if chunk_count > 1 else "تم تحسين القصة."
            ),
            result_summary={"improved_text": improved_text, "chunk_count": chunk_count, "latency_ms": latency_ms},
        )
    except OllamaError as exc:
        job_store.update(
            job_id, status="failed", finished_at=now_iso(), safe_error_ar=str(exc), message_ar="فشل تحسين القصة."
        )
    except Exception:
        job_store.update(
            job_id,
            status="failed",
            finished_at=now_iso(),
            safe_error_ar="حدث خطأ غير متوقع أثناء تحسين القصة.",
            message_ar="فشل تحسين القصة.",
        )


@router.post("/story/improve", response_model=ApiEnvelope)
@router.post("/story/improve-narration", response_model=ApiEnvelope)
def improve_story(
    request: ImproveStoryRequest,
    provider: OllamaProvider = Depends(get_provider),
    settings: Settings = Depends(get_settings),
) -> ApiEnvelope:
    try:
        engine = StoryEngine(provider)
        improved_text, latency_ms, chunk_count = engine.improve_narration_script(
            story_text=request.story_text,
            tone=request.tone,
            language=request.language,
            chunk_chars=settings.long_story_chunk_chars,
        )
        return ApiEnvelope(
            data={"improved_text": improved_text},
            meta={
                "provider": "ollama",
                "model": provider.model,
                "latency_ms": latency_ms,
                "chunk_count": chunk_count,
                "limitations": ["AI output requires human review"],
            },
        )
    except OllamaError as exc:
        return ApiEnvelope(
            data={"improved_text": ""},
            meta={"provider": "ollama", "model": provider.model},
            errors=[str(exc)],
        )


@router.post("/projects/{project_id}/story/improve/jobs", response_model=ApiEnvelope)
def improve_story_job(
    project_id: str,
    request: ImproveStoryRequest,
    background_tasks: BackgroundTasks,
    provider: OllamaProvider = Depends(get_provider),
    settings: Settings = Depends(get_settings),
    store: JobStore = Depends(get_store),
) -> ApiEnvelope:
    """Job-based variant of /story/improve -- returns immediately with a job_id
    to poll instead of blocking the request for the whole (possibly chunked)
    improve operation. The original synchronous endpoint is unchanged and still
    works for callers that don't need progress polling."""
    job = store.create(project_id, "story_improve", total_steps=1, message_ar="في قائمة الانتظار...")
    background_tasks.add_task(
        _run_improve_job,
        store,
        job.job_id,
        provider,
        request.story_text,
        request.tone,
        request.language,
        settings.long_story_chunk_chars,
    )
    return ApiEnvelope(data=job.to_dict(), meta={"provider": "ollama"})


@router.post("/story/split-scenes", response_model=ApiEnvelope)
def split_scenes(
    request: SplitScenesRequest,
    provider: OllamaProvider = Depends(get_provider),
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    try:
        engine = StoryEngine(provider)
        split_data, latency_ms = engine.split_into_scenes(request)
        saved_data = storage.save_story_project(
            story_text=request.story_text,
            split_data=split_data,
            provider="ollama",
            model=provider.model,
        )
        return ApiEnvelope(
            data=saved_data.model_dump(),
            meta={
                "provider": "ollama",
                "model": provider.model,
                "latency_ms": latency_ms,
                "limitations": ["AI output requires human review"],
            },
        )
    except (OllamaError, StoryEngineError) as exc:
        return ApiEnvelope(
            data={"project_id": None, "story_title": request.title, "scenes": []},
            meta={"provider": "ollama", "model": provider.model},
            errors=[str(exc)],
        )
