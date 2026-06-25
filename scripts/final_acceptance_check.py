"""Final acceptance check for the AI Story Studio Production MVP.

Exercises the backend end-to-end over HTTP only: health/config/worker
health, project CRUD, scene edit, scenes.json, subtitles, export.zip,
and per-project asset metadata endpoints (audio/images/video). Does
NOT call Ollama (no story improve/split) and does NOT trigger any
TTS/image generation job, so it never produces AI media and runs fast
even when the AI Server / workers are unreachable.

Never prints story/scene text content, only status/structure.
Run with the backend already up (e.g. `docker compose up -d backend`).
"""

from __future__ import annotations

import io
import json
import os
import sys
import urllib.error
import urllib.request
import zipfile

BASE_URL = os.environ.get("SMOKE_BASE_URL", "http://localhost:8810")


def request(method: str, path: str, body: dict | None = None) -> tuple[int, bytes]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        sys.exit(1)


def main() -> None:
    status, body = request("GET", "/health")
    check("GET /health returns 200", status == 200)
    check("health status is ok", json.loads(body)["data"]["status"] == "ok")

    status, body = request("GET", "/api/config")
    check("GET /api/config returns 200", status == 200)

    status, _ = request("GET", "/api/tts/health")
    check("GET /api/tts/health returns 200", status == 200)

    status, _ = request("GET", "/api/images/health")
    check("GET /api/images/health returns 200", status == 200)

    status, body = request(
        "POST",
        "/api/projects",
        {
            "title": "Acceptance Check Project",
            "original_story": "نص اختبار قبول قصير.",
            "improved_story": "",
            "scenes": [
                {
                    "scene_id": "01",
                    "title_ar": "مشهد اختبار",
                    "narration_ar": "نص راوٍ قصير للاختبار فقط.",
                    "visual_description_ar": "وصف بصري للاختبار.",
                    "image_prompt_en": "test scene prompt",
                    "duration_seconds": 5,
                }
            ],
        },
    )
    check("POST /api/projects returns 200", status == 200)
    project = json.loads(body)["data"]
    project_id = project["project_id"]
    check("created project has 1 scene", len(project["scenes"]) == 1)

    status, body = request(
        "PUT",
        f"/api/projects/{project_id}",
        {"scenes": [{**project["scenes"][0], "title_ar": "مشهد محرر", "duration_seconds": 9}]},
    )
    check("PUT /api/projects/{id} (scene edit) returns 200", status == 200)
    updated = json.loads(body)["data"]
    check("edited scene duration persisted", updated["scenes"][0]["duration_seconds"] == 9)

    status, _ = request("GET", f"/api/projects/{project_id}/scenes.json")
    check("GET .../scenes.json returns 200", status == 200)

    status, body = request("GET", f"/api/projects/{project_id}/subtitles.srt")
    check("GET .../subtitles.srt returns 200", status == 200)
    check("subtitles.srt body is non-empty", len(body) > 0)

    status, body = request("GET", f"/api/projects/{project_id}/subtitles.vtt")
    check("GET .../subtitles.vtt returns 200", status == 200)
    check("subtitles.vtt has WEBVTT header", body.startswith(b"WEBVTT"))

    status, body = request("GET", f"/api/projects/{project_id}/audio")
    check("GET .../audio returns 200", status == 200)
    audio_data = json.loads(body)["data"]
    check("no audio generated yet (expected, no TTS job run)", not audio_data["final_story"]["has_audio"])

    status, body = request("GET", f"/api/projects/{project_id}/images")
    check("GET .../images returns 200", status == 200)
    images_data = json.loads(body)["data"]
    check("no images generated yet (expected, no image job run)", not any(s["has_image"] for s in images_data["scenes"]))

    status, body = request("GET", f"/api/projects/{project_id}/video")
    check("GET .../video returns 200", status == 200)
    check("no video rendered yet (expected)", not json.loads(body)["data"]["has_video"])

    status, body = request("GET", f"/api/projects/{project_id}/export.zip")
    check("GET .../export.zip returns 200", status == 200)
    zf = zipfile.ZipFile(io.BytesIO(body))
    names = set(zf.namelist())
    for expected in ("story.txt", "scenes.json", "metadata.json", "subtitles/story.srt", "subtitles/story.vtt"):
        check(f"export.zip contains {expected}", expected in names)
    check("export.zip has no stray audio/images/video (none generated)", not any(
        n.startswith(("audio/", "images/", "video/")) for n in names
    ))

    status, _ = request("GET", "/api/projects/00000000-0000-0000-0000-000000000000")
    check("GET nonexistent project returns 404", status == 404)

    status, _ = request("DELETE", f"/api/projects/{project_id}")
    check("DELETE /api/projects/{id} returns 200", status == 200)

    print("Final acceptance check passed.")


if __name__ == "__main__":
    main()
