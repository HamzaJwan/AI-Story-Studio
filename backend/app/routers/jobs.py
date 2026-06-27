from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.jobs import JobStore, get_job_store
from app.schemas import ApiEnvelope

router = APIRouter(tags=["jobs"])

_TERMINAL_STATUSES = {"done", "failed", "cancelled"}


def get_store(settings: Settings = Depends(get_settings)) -> JobStore:
    return get_job_store(settings.data_path)


@router.get("/api/jobs/{job_id}", response_model=ApiEnvelope)
def get_job(job_id: str, store: JobStore = Depends(get_store)) -> ApiEnvelope:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return ApiEnvelope(data=job.to_dict())


@router.get("/api/projects/{project_id}/jobs", response_model=ApiEnvelope)
def list_project_jobs(project_id: str, store: JobStore = Depends(get_store)) -> ApiEnvelope:
    jobs = store.list_for_project(project_id)
    return ApiEnvelope(data={"project_id": project_id, "jobs": [job.to_dict() for job in jobs]})


@router.post("/api/jobs/{job_id}/cancel", response_model=ApiEnvelope)
def cancel_job(job_id: str, store: JobStore = Depends(get_store)) -> ApiEnvelope:
    """Milestone 6 -- cooperative cancel. Only sets `cancel_requested`; the
    running job (story improve, currently the only job type that checks this)
    notices it at the next safe point -- between stream events, between
    chunks, or between recovery splits -- and transitions to `cancelled`
    itself. This endpoint never deletes the job or forces it to stop
    instantly, since a provider call already in flight cannot be interrupted
    until it next checks `should_cancel()`."""
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status in _TERMINAL_STATUSES:
        return ApiEnvelope(data=job.to_dict(), meta={"already_finished": True})
    store.update(
        job_id,
        cancel_requested=True,
        message_ar="تم طلب الإلغاء، سيتم الإيقاف عند أول نقطة آمنة.",
    )
    updated = store.get(job_id)
    return ApiEnvelope(data=updated.to_dict() if updated else job.to_dict())
