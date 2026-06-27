from __future__ import annotations

import time

from fastapi import APIRouter, BackgroundTasks, Depends

from app.ai_providers.ollama import OllamaError, OllamaProvider
from app.config import Settings, get_settings
from app.jobs import JobStore, get_job_store, now_iso
from app.routers.ollama import get_provider
from app.schemas import ApiEnvelope, ImproveStoryRequest, SplitScenesRequest
from app.storage import ProjectStorage
from app.story_engine.engine import (
    AUTO_TONE_VALUE,
    StoryCancelledError,
    StoryDeadlineExceededError,
    StoryEngine,
    StoryEngineError,
    ToneAnalysis,
)

router = APIRouter(prefix="/api", tags=["story"])

# How often (seconds) the throttled cancel-check / stream-activity callbacks
# below are allowed to actually touch the job JSON file. Stream activity can
# fire once per generated token -- without this, a single chunk could mean
# hundreds of disk writes for no real UX benefit.
_PROGRESS_WRITE_THROTTLE_SECONDS = 1.0


def get_storage(settings: Settings = Depends(get_settings)) -> ProjectStorage:
    return ProjectStorage(settings)


def get_store(settings: Settings = Depends(get_settings)) -> JobStore:
    return get_job_store(settings.data_path)


def _make_should_cancel(store: JobStore, job_id: str):
    """Cooperative cancel check (Milestone 6), throttled to at most one disk
    read per second regardless of how often the caller polls it -- streaming
    callbacks can fire once per token."""
    state = {"checked_at": 0.0, "cancelled": False}

    def should_cancel() -> bool:
        now = time.monotonic()
        if now - state["checked_at"] < _PROGRESS_WRITE_THROTTLE_SECONDS:
            return state["cancelled"]
        state["checked_at"] = now
        job = store.get(job_id)
        state["cancelled"] = bool(job and job.cancel_requested)
        return state["cancelled"]

    return should_cancel


def _make_on_stream_activity(store: JobStore, job_id: str):
    """Live activity feed (Milestone 5), throttled the same way -- records
    `generated_units`/`last_activity_at` without writing on every token."""
    state = {"written_at": 0.0}

    def on_stream_activity(generated_units: int, _elapsed_seconds: float) -> None:
        now = time.monotonic()
        if now - state["written_at"] < _PROGRESS_WRITE_THROTTLE_SECONDS:
            return
        state["written_at"] = now
        store.update(job_id, generated_units=generated_units, last_activity_at=now_iso())

    return on_stream_activity


def _run_improve_job(
    job_store: JobStore,
    job_id: str,
    provider: OllamaProvider,
    story_text: str,
    tone: str,
    language: str,
    title: str,
    chunk_chars: int,
    max_total_seconds: int,
) -> None:
    started_monotonic = time.monotonic()
    deadline_monotonic = started_monotonic + max_total_seconds
    job_store.update(
        job_id,
        status="running",
        started_at=now_iso(),
        phase="analyzing" if tone == "تلقائي" else "preparing_chunks",
        message_ar="جاري تحليل القصة..." if tone == "تلقائي" else "جاري تحسين القصة...",
        last_activity_at=now_iso(),
    )
    should_cancel = _make_should_cancel(job_store, job_id)
    on_stream_activity = _make_on_stream_activity(job_store, job_id)
    completed_chunk_durations: list[float] = []

    def on_progress(index: int, total: int) -> None:
        job_store.update(
            job_id,
            phase="generating",
            current_step=index,
            total_steps=total,
            completed_steps=index - 1,
            message_ar=f"جاري تحسين الجزء {index} من {total}...",
            last_activity_at=now_iso(),
        )

    def on_tone_resolved(analysis: ToneAnalysis) -> None:
        if tone != AUTO_TONE_VALUE:
            return
        message = f"النبرة المقترحة: {analysis.resolved_tone}"
        if analysis.reason_ar:
            message += f" — لأن {analysis.reason_ar}"
        job_store.update(
            job_id,
            phase="preparing_chunks",
            message_ar=message,
            last_activity_at=now_iso(),
            result_summary={
                "requested_tone": analysis.requested_tone,
                "resolved_tone": analysis.resolved_tone,
                "genre": analysis.genre,
                "pacing": analysis.pacing,
                "reason_ar": analysis.reason_ar,
                "analysis_fallback": analysis.analysis_fallback,
            },
        )

    def on_retry_notice(message: str) -> None:
        # A chunk timed out/truncated and is being split/retried -- surface
        # this live via the job's message_ar instead of leaving the user on
        # a stale "جاري تحسين الجزء..." message during the extra recovery time.
        current = job_store.get(job_id)
        job_store.update(
            job_id,
            phase="retrying",
            message_ar=message,
            last_activity_at=now_iso(),
            retry_count=(current.retry_count + 1) if current else 1,
        )

    def on_chunk_complete(index: int, total: int, chunk_seconds: float) -> None:
        completed_chunk_durations.append(chunk_seconds)
        average_seconds = sum(completed_chunk_durations) / len(completed_chunk_durations)
        remaining_chunks = total - index
        progress_percent = round((index / total) * 100, 1) if total else None
        job_store.update(
            job_id,
            completed_steps=index,
            progress_percent=progress_percent,
            estimated_remaining_seconds=round(average_seconds * remaining_chunks, 1),
            last_activity_at=now_iso(),
        )

    try:
        engine = StoryEngine(provider)
        result = engine.improve_narration_script(
            story_text=story_text,
            tone=tone,
            language=language,
            chunk_chars=chunk_chars,
            title=title,
            on_progress=on_progress,
            on_retry_notice=on_retry_notice,
            on_chunk_complete=on_chunk_complete,
            on_stream_activity=on_stream_activity,
            on_tone_resolved=on_tone_resolved,
            should_cancel=should_cancel,
            deadline_monotonic=deadline_monotonic,
            use_streaming=True,
        )
        job_store.update(job_id, phase="assembling", message_ar="جاري تجميع النتيجة النهائية...")
        elapsed_seconds = round(time.monotonic() - started_monotonic, 1)
        job_store.update(
            job_id,
            status="done",
            phase="done",
            current_step=result.chunk_count,
            total_steps=result.chunk_count,
            completed_steps=result.chunk_count,
            progress_percent=100.0,
            estimated_remaining_seconds=0,
            elapsed_seconds=elapsed_seconds,
            finished_at=now_iso(),
            message_ar=(
                f"تم تحسين القصة على {result.chunk_count} أجزاء." if result.chunk_count > 1 else "تم تحسين القصة."
            ),
            result_summary={
                "improved_text": result.improved_text,
                "chunk_count": result.chunk_count,
                "latency_ms": result.latency_ms,
                "requested_tone": result.requested_tone,
                "resolved_tone": result.resolved_tone,
                "genre": result.genre,
                "pacing": result.pacing,
                "reason_ar": result.reason_ar,
                "analysis_fallback": result.analysis_fallback,
            },
        )
    except StoryCancelledError as exc:
        job_store.update(
            job_id,
            status="cancelled",
            phase="cancelled",
            finished_at=now_iso(),
            elapsed_seconds=round(time.monotonic() - started_monotonic, 1),
            safe_error_ar=str(exc),
            message_ar="تم إلغاء تحسين القصة.",
        )
    except StoryDeadlineExceededError as exc:
        job_store.update(
            job_id,
            status="failed",
            phase="failed",
            finished_at=now_iso(),
            elapsed_seconds=round(time.monotonic() - started_monotonic, 1),
            safe_error_ar=str(exc),
            message_ar="فشل تحسين القصة.",
        )
    except (OllamaError, StoryEngineError) as exc:
        job_store.update(
            job_id,
            status="failed",
            phase="failed",
            finished_at=now_iso(),
            elapsed_seconds=round(time.monotonic() - started_monotonic, 1),
            safe_error_ar=str(exc),
            message_ar="فشل تحسين القصة.",
        )
    except Exception:
        job_store.update(
            job_id,
            status="failed",
            phase="failed",
            finished_at=now_iso(),
            elapsed_seconds=round(time.monotonic() - started_monotonic, 1),
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
        deadline_monotonic = time.monotonic() + settings.long_story_max_total_seconds
        result = engine.improve_narration_script(
            story_text=request.story_text,
            tone=request.tone,
            language=request.language,
            chunk_chars=settings.long_story_chunk_chars,
            title=request.title,
            deadline_monotonic=deadline_monotonic,
        )
        return ApiEnvelope(
            data={"improved_text": result.improved_text},
            meta={
                "provider": "ollama",
                "model": provider.model,
                "latency_ms": result.latency_ms,
                "chunk_count": result.chunk_count,
                "requested_tone": result.requested_tone,
                "resolved_tone": result.resolved_tone,
                "genre": result.genre,
                "pacing": result.pacing,
                "reason_ar": result.reason_ar,
                "analysis_fallback": result.analysis_fallback,
                "limitations": ["AI output requires human review"],
            },
        )
    except (OllamaError, StoryEngineError) as exc:
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
    improve operation. The original synchronous endpoint is unchanged and
    still works for callers that don't need progress polling/cancel. Uses
    Ollama streaming internally (Milestone 2) so the job shows real activity
    instead of staying frozen until the whole chunk finishes."""
    job = store.create(project_id, "story_improve", total_steps=1, message_ar="في قائمة الانتظار...")
    background_tasks.add_task(
        _run_improve_job,
        store,
        job.job_id,
        provider,
        request.story_text,
        request.tone,
        request.language,
        request.title,
        settings.long_story_chunk_chars,
        settings.long_story_max_total_seconds,
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
