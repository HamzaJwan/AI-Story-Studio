"""Lightweight local job/progress tracking -- Milestone A of the Production
Studio RC2 fix pack (2026-06-25).

Deliberately NOT a real job queue: no Redis, no Celery, no DB. Each job is a
small JSON file under `data/jobs/{job_id}.json`, updated in place while a
FastAPI BackgroundTask runs the real work (story improve, image/audio
generate-all, video render). This only solves the "stuck on جاري..." UX
problem -- it does not add retries, distributed workers, or persistence
guarantees beyond a single local process.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

JobStatus = Literal["queued", "running", "done", "failed", "cancelled"]

_LOCK = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobRecord:
    job_id: str
    project_id: str
    job_type: str
    status: JobStatus = "queued"
    current_step: int = 0
    total_steps: int = 1
    completed_steps: int = 0
    message_ar: str = ""
    safe_error_ar: str | None = None
    started_at: str | None = None
    updated_at: str = ""
    finished_at: str | None = None
    result_summary: dict[str, Any] | None = None
    affected_scene_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class JobStore:
    def __init__(self, jobs_dir: Path):
        self.jobs_dir = jobs_dir
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        return self.jobs_dir / f"{job_id}.json"

    def create(
        self,
        project_id: str,
        job_type: str,
        total_steps: int = 1,
        message_ar: str = "في قائمة الانتظار...",
    ) -> JobRecord:
        job = JobRecord(
            job_id=str(uuid.uuid4()),
            project_id=project_id,
            job_type=job_type,
            status="queued",
            total_steps=max(total_steps, 1),
            message_ar=message_ar,
            updated_at=now_iso(),
        )
        self._write(job)
        return job

    def get(self, job_id: str) -> JobRecord | None:
        path = self._path(job_id)
        if not path.exists():
            return None
        with _LOCK:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
        return JobRecord(**data)

    def list_for_project(self, project_id: str) -> list[JobRecord]:
        jobs: list[JobRecord] = []
        for path in self.jobs_dir.glob("*.json"):
            with _LOCK:
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
            if data.get("project_id") == project_id:
                jobs.append(JobRecord(**data))
        jobs.sort(key=lambda j: j.updated_at, reverse=True)
        return jobs

    def update(self, job_id: str, **fields: Any) -> None:
        with _LOCK:
            path = self._path(job_id)
            if not path.exists():
                return
            data = json.loads(path.read_text(encoding="utf-8"))
            data.update(fields)
            data["updated_at"] = now_iso()
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write(self, job: JobRecord) -> None:
        with _LOCK:
            self._path(job.job_id).write_text(
                json.dumps(job.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
            )


def get_job_store(data_dir: Path) -> JobStore:
    return JobStore(data_dir / "jobs")
