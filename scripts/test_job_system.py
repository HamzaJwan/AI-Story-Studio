"""Regression test for the Milestone A lightweight job/progress system
(2026-06-25): job-based endpoints must return immediately with a job_id,
and GET /api/jobs/{job_id} must reach a terminal status (done/failed) with
sane progress fields, instead of leaving the UI stuck on a vague spinner.

Self-contained, hits the live backend over HTTP only. Uses a synthetic
throwaway project with a tiny real WAV+PNG (same fixtures as
test_video_audio_duration_sync.py) so the video/render job path can be
exercised without any AI Server call. Prints only structural facts.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

BASE_URL = os.environ.get("SMOKE_BASE_URL", "http://localhost:8810")
DATA_DIR = Path(os.environ.get("SMOKE_DATA_DIR", "data"))

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def request(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        sys.exit(1)


def write_silent_wav(path: Path, seconds: float, rate: int = 16000) -> None:
    frame_count = int(seconds * rate)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(b"\x00\x00" * frame_count)


def wait_for_terminal(job_id: str, max_wait_seconds: int = 60) -> dict:
    deadline = time.time() + max_wait_seconds
    last_job: dict = {}
    while time.time() < deadline:
        status, body = request("GET", f"/api/jobs/{job_id}")
        check("GET /api/jobs/{job_id} returns 200", status == 200)
        last_job = body["data"]
        if last_job["status"] in ("done", "failed", "cancelled"):
            return last_job
        time.sleep(0.5)
    check(f"job {job_id} reached a terminal status within {max_wait_seconds}s", False)
    return last_job


def main() -> None:
    status, body = request(
        "POST",
        "/api/projects",
        {
            "title": "Job System Test (throwaway)",
            "original_story": "",
            "improved_story": "",
            "scenes": [
                {
                    "scene_id": "01",
                    "title_ar": "scene 01",
                    "narration_ar": "narration 01",
                    "visual_description_ar": "visual 01",
                    "image_prompt_en": "prompt 01",
                    "duration_seconds": 8,
                },
                {
                    "scene_id": "02",
                    "title_ar": "scene 02",
                    "narration_ar": "narration 02",
                    "visual_description_ar": "visual 02",
                    "image_prompt_en": "prompt 02",
                    "duration_seconds": 8,
                },
            ],
        },
    )
    check("create test project returns 200", status == 200)
    project = body["data"]
    project_id = project["project_id"]
    project_dir = DATA_DIR / "projects" / project_id

    try:
        audio_dir = project_dir / "audio"
        images_dir = project_dir / "images"
        audio_dir.mkdir(parents=True, exist_ok=True)
        images_dir.mkdir(parents=True, exist_ok=True)

        scenes = project["scenes"]
        for scene in scenes:
            write_silent_wav(audio_dir / f"scene_{scene['scene_id']}.wav", 3.0)
            (images_dir / f"scene_{scene['scene_id']}.png").write_bytes(TINY_PNG)
            scene["audio_format"] = "wav"
            scene["audio_bytes"] = int(3.0 * 16000 * 2)
            scene["image_format"] = "png"
            scene["image_bytes"] = len(TINY_PNG)
            scene["image_width"] = 1
            scene["image_height"] = 1

        status, _ = request("PUT", f"/api/projects/{project_id}", {"scenes": scenes})
        check("attach synthetic audio/image metadata returns 200", status == 200)

        # 1) Job-based video render: must return a job_id immediately (queued/running),
        #    not block until the render finishes.
        started = time.time()
        status, body = request("POST", f"/api/projects/{project_id}/video/render/jobs")
        elapsed = time.time() - started
        check("POST video/render/jobs returns 200", status == 200)
        job = body["data"]
        check("video render job starts in queued/running status", job["status"] in ("queued", "running"))
        check("video render job creation returns quickly (<3s, not the full render)", elapsed < 3)
        print(f"[INFO] video_render_job_id={job['job_id']} initial_status={job['status']} create_latency_s={elapsed:.2f}")

        final_job = wait_for_terminal(job["job_id"])
        check("video render job finished with status=done", final_job["status"] == "done")
        check("video render job completed_steps == total_steps", final_job["completed_steps"] == final_job["total_steps"])
        check("video render job result_summary has duration_seconds", "duration_seconds" in (final_job.get("result_summary") or {}))
        print(
            f"[INFO] video_render_job_status={final_job['status']} "
            f"completed_steps={final_job['completed_steps']} total_steps={final_job['total_steps']} "
            f"duration_seconds={(final_job.get('result_summary') or {}).get('duration_seconds')}"
        )

        # 2) GET /api/projects/{project_id}/jobs lists it.
        status, body = request("GET", f"/api/projects/{project_id}/jobs")
        check("GET /api/projects/{id}/jobs returns 200", status == 200)
        jobs_list = body["data"]["jobs"]
        check("project jobs list contains the render job", any(j["job_id"] == job["job_id"] for j in jobs_list))
        print(f"[INFO] project_jobs_count={len(jobs_list)}")

        # 3) Job for a nonexistent project must 404 cleanly, not raise.
        status, _ = request("GET", "/api/jobs/does-not-exist")
        check("GET /api/jobs/{bad_id} returns 404", status == 404)

        print("Job system test passed.")
    finally:
        request("DELETE", f"/api/projects/{project_id}")
        shutil.rmtree(project_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
