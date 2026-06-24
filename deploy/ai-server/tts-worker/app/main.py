from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from worker_app import jobs

app = FastAPI(title="AI Story Studio — TTS Worker (lab)")


class TtsJobRequest(BaseModel):
    text: str
    voice_id: str | None = None
    speed: float | None = None
    format: str = "wav"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "device": jobs.detect_device(), "engine": jobs.ENGINE}


@app.post("/api/tts/jobs")
def create_job(request: TtsJobRequest) -> dict:
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="text is required.")
    return jobs.create_job(request.text, request.voice_id, request.speed, request.format)


@app.get("/api/tts/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/api/tts/jobs/{job_id}/files")
def get_job_files(job_id: str) -> dict:
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    files = [
        {
            "format": f["format"],
            "bytes": f["bytes"],
            "url": f"/api/tts/jobs/{job_id}/download/{f['format']}",
        }
        for f in job.get("files", [])
    ]
    return {"job_id": job_id, "status": job["status"], "files": files}


@app.get("/api/tts/jobs/{job_id}/download/{fmt}")
def download_job_file(job_id: str, fmt: str) -> FileResponse:
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    match = next((f for f in job.get("files", []) if f["format"] == fmt), None)
    if not match:
        raise HTTPException(status_code=404, detail="File not found for this job.")
    path = Path(match["path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk.")
    media_type = "audio/wav" if fmt == "wav" else "audio/mpeg"
    return FileResponse(path, media_type=media_type, filename=f"{job_id}.{fmt}")
