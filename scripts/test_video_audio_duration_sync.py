"""Regression test for the manual-QA Issue 2 fix (2026-06-25): rendered
video duration and subtitle timing must follow each scene's REAL saved
audio duration, not the fixed `duration_seconds` estimate.

Self-contained and fully synthetic -- no Ollama, no TTS worker, no
ComfyUI/image job. Creates a throwaway project with `duration_seconds`
deliberately set wrong (8s/scene), writes a silent WAV of a known exact
length (via the stdlib `wave` module) and a tiny 1x1 PNG directly into
the project's data directory, renders the video, and checks ffprobe's
real duration plus the subtitle cue timing against the real audio
total -- proving the fixed estimate is no longer what drives duration.

Always deletes the test project (API + filesystem) when done.
Requires the backend to be up and ffprobe on PATH (same requirement as
the backend's own video assembly).
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import wave
from pathlib import Path

HAVE_FFPROBE = shutil.which("ffprobe") is not None

BASE_URL = os.environ.get("SMOKE_BASE_URL", "http://localhost:8810")
DATA_DIR = Path(os.environ.get("SMOKE_DATA_DIR", "data"))

# Minimal valid 1x1 black PNG, hardcoded -- avoids adding Pillow as a dependency.
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

SCENE_AUDIO_SECONDS = [3.0, 5.0]  # real synthetic audio, deliberately != duration_seconds below
WRONG_DURATION_SECONDS = 8  # stale fixed estimate this test proves is no longer used
EXPECTED_TOTAL = sum(SCENE_AUDIO_SECONDS)


def request(method: str, path: str, body: dict | None = None) -> tuple[int, bytes]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


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


def ffprobe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    return float(result.stdout.strip())


def make_scene(scene_id: str) -> dict:
    return {
        "scene_id": scene_id,
        "title_ar": f"scene {scene_id}",
        "narration_ar": f"narration {scene_id}",
        "visual_description_ar": f"visual {scene_id}",
        "image_prompt_en": f"prompt {scene_id}",
        "duration_seconds": WRONG_DURATION_SECONDS,
    }


def main() -> None:
    status, body = request(
        "POST",
        "/api/projects",
        {
            "title": "Duration Sync Test (throwaway)",
            "original_story": "",
            "improved_story": "",
            "scenes": [make_scene("01"), make_scene("02")],
        },
    )
    check("create test project returns 200", status == 200)
    project = json.loads(body)["data"]
    project_id = project["project_id"]
    project_dir = DATA_DIR / "projects" / project_id

    try:
        audio_dir = project_dir / "audio"
        images_dir = project_dir / "images"
        audio_dir.mkdir(parents=True, exist_ok=True)
        images_dir.mkdir(parents=True, exist_ok=True)

        scenes = project["scenes"]
        for scene, seconds in zip(scenes, SCENE_AUDIO_SECONDS):
            write_silent_wav(audio_dir / f"scene_{scene['scene_id']}.wav", seconds)
            (images_dir / f"scene_{scene['scene_id']}.png").write_bytes(TINY_PNG)
            scene["audio_format"] = "wav"
            scene["audio_bytes"] = int(seconds * 16000 * 2)
            scene["image_format"] = "png"
            scene["image_bytes"] = len(TINY_PNG)
            scene["image_width"] = 1
            scene["image_height"] = 1

        status, _ = request("PUT", f"/api/projects/{project_id}", {"scenes": scenes})
        check("attach synthetic audio/image metadata returns 200", status == 200)

        status, body = request("POST", f"/api/projects/{project_id}/video/render")
        check("render video returns 200", status == 200)
        render_data = json.loads(body)["data"]
        wrong_total = len(SCENE_AUDIO_SECONDS) * WRONG_DURATION_SECONDS
        check(
            f"rendered duration_seconds={render_data['duration_seconds']} is close to real audio "
            f"total={EXPECTED_TOTAL}s, not the wrong fixed estimate={wrong_total}s",
            abs(render_data["duration_seconds"] - EXPECTED_TOTAL) < 1.5,
        )

        video_path = project_dir / "video" / "final_story.mp4"
        check("rendered MP4 exists on disk", video_path.exists())
        if HAVE_FFPROBE:
            real_duration = ffprobe_duration(video_path)
            check(
                f"ffprobe MP4 duration={real_duration:.2f}s matches real audio total={EXPECTED_TOTAL}s within 1.5s",
                abs(real_duration - EXPECTED_TOTAL) < 1.5,
            )
        else:
            print(
                "[SKIP] ffprobe not found on this host's PATH (it only runs inside the backend "
                "container) -- relying on the API's own duration_seconds + subtitle timing checks instead."
            )

        status, body = request("GET", f"/api/projects/{project_id}/subtitles.srt")
        check("GET subtitles.srt returns 200", status == 200)
        srt_text = body.decode("utf-8")
        timestamps = re.findall(r"--> (\d\d):(\d\d):(\d\d),(\d\d\d)", srt_text)
        check("subtitles.srt has 2 cues", len(timestamps) == 2)
        h, m, s, ms = timestamps[-1]
        last_end_seconds = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        check(
            f"last subtitle cue end={last_end_seconds:.2f}s matches real audio total={EXPECTED_TOTAL}s within 0.1s",
            abs(last_end_seconds - EXPECTED_TOTAL) < 0.1,
        )

        print("Video/audio duration sync test passed.")
    finally:
        request("DELETE", f"/api/projects/{project_id}")
        shutil.rmtree(project_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
