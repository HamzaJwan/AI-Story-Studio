"""Regression test for Milestone E (Ken Burns / Better Video Assembly,
2026-06-26): the `ken_burns` zoompan filter and `fade` in/out transition must
still produce a playable MP4 whose duration matches the real per-scene audio
total -- the Milestone 0 duration-sync guarantee must hold for every video
mode, not just `static`.

Self-contained, hits the live backend over HTTP only. Uses a synthetic
6-scene throwaway project with tiny real WAV+PNG fixtures (same pattern as
test_video_audio_duration_sync.py) so this never depends on a real AI Server
image/TTS job. Prints only structural facts.
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

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

SCENE_COUNT = 6
SECONDS_PER_SCENE = 2.0
EXPECTED_TOTAL = SCENE_COUNT * SECONDS_PER_SCENE


def request(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
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
        "duration_seconds": 8,  # deliberately wrong estimate; real audio should win
    }


def main() -> None:
    scene_ids = [f"{i:02d}" for i in range(1, SCENE_COUNT + 1)]
    status, body = request(
        "POST",
        "/api/projects",
        {
            "title": "Ken Burns Test (throwaway)",
            "video_mode": "ken_burns",
            "video_transition": "fade",
            "scenes": [make_scene(sid) for sid in scene_ids],
        },
    )
    check("create 6-scene ken_burns project returns 200", status == 200)
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
            write_silent_wav(audio_dir / f"scene_{scene['scene_id']}.wav", SECONDS_PER_SCENE)
            (images_dir / f"scene_{scene['scene_id']}.png").write_bytes(TINY_PNG)
            scene["audio_format"] = "wav"
            scene["audio_bytes"] = int(SECONDS_PER_SCENE * 16000 * 2)
            scene["image_format"] = "png"
            scene["image_bytes"] = len(TINY_PNG)
            scene["image_width"] = 1
            scene["image_height"] = 1

        status, _ = request("PUT", f"/api/projects/{project_id}", {"scenes": scenes})
        check("attach synthetic audio/image metadata returns 200", status == 200)

        status, body = request("POST", f"/api/projects/{project_id}/video/render")
        check("render ken_burns+fade video returns 200", status == 200)
        render_data = body["data"]
        check("rendered video_mode is ken_burns", render_data["video_mode"] == "ken_burns")
        check("rendered video_transition is fade", render_data["video_transition"] == "fade")
        check(
            f"rendered duration_seconds={render_data['duration_seconds']} matches real audio "
            f"total={EXPECTED_TOTAL}s within 1.5s (Milestone 0 guarantee holds for ken_burns too)",
            abs(render_data["duration_seconds"] - EXPECTED_TOTAL) < 1.5,
        )
        check("all 6 scenes included, none skipped", len(render_data["included_scenes"]) == SCENE_COUNT)

        video_path = project_dir / "video" / "final_story.mp4"
        check("rendered MP4 exists on disk", video_path.exists())
        if HAVE_FFPROBE:
            real_duration = ffprobe_duration(video_path)
            check(
                f"ffprobe MP4 duration={real_duration:.2f}s matches real audio total={EXPECTED_TOTAL}s within 1.5s",
                abs(real_duration - EXPECTED_TOTAL) < 1.5,
            )
        else:
            print("[SKIP] ffprobe not found on this host's PATH -- relying on the API's own duration_seconds.")

        # subtitles.srt is plain text, not JSON -- fetch it directly instead of
        # through the json-decoding request() helper used for the API above.
        srt_response = urllib.request.urlopen(f"{BASE_URL}/api/projects/{project_id}/subtitles.srt", timeout=15)
        check("GET subtitles.srt returns 200", srt_response.status == 200)
        raw = srt_response.read()
        timestamps = re.findall(r"--> (\d\d):(\d\d):(\d\d),(\d\d\d)", raw.decode("utf-8"))
        check(f"subtitles.srt has {SCENE_COUNT} cues", len(timestamps) == SCENE_COUNT)

        print("Ken Burns video assembly test passed.")
    finally:
        request("DELETE", f"/api/projects/{project_id}")
        shutil.rmtree(project_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
