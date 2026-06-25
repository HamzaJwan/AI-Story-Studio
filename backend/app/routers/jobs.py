from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.jobs import JobStore, get_job_store
from app.schemas import ApiEnvelope

router = APIRouter(tags=["jobs"])


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
