"""Regression test for the 2026-06-28 "Project Audio Persistence and Video
Integration" fix pack.

Hamza's report: after generating audio for the whole project, audio either
didn't reliably show as saved, or the rendered video appeared to not use it.
Forensic finding (proven with a real ffmpeg experiment, not assumed): when
some scenes have saved audio and others don't, the old code rendered
audio-less segments with `-an` (no audio stream at all). The final
concatenation step uses `-c copy`, which requires every segment to share the
same stream layout -- mixing `-an` segments with audio-having segments
desyncs/drops audio for the *entire rest* of the concatenated video, not just
the one scene missing it (verified with `ffprobe`/`silencedetect` on a 3-
segment test clip: real/none/real audio in -> broken audio out; same clip
with a silent track instead of `-an` -> correct 3s-silence-in-the-middle
result). The fix makes every segment carry an audio stream (real or a silent
`anullsrc` track of the same duration), so `-c copy` concatenation is always
stream-consistent, plus adds a post-render `ffprobe` safety check and richer
per-scene `scene_details` metadata.

Uses the REAL TTS worker (confirmed reachable in this environment via
`GET /api/tts/health`) for actual generate-all persistence, and synthetic
PNG fixtures for images (the existing project convention -- see
`test_video_audio_duration_sync.py`) since image generation is not the
subject of this fix and would add unnecessary AI Server load. Skips
gracefully if the TTS worker is not reachable. Always deletes its test
project. Never prints narration/audio content.
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
from io import BytesIO
from pathlib import Path

BASE_URL = os.environ.get("SMOKE_BASE_URL", "http://localhost:8810")
DATA_DIR = Path(os.environ.get("SMOKE_DATA_DIR", "data"))
# ffmpeg/ffprobe only exist inside the backend container, not the Windows
# host (documented project constraint, same as test_video_audio_duration_sync.py)
# -- the ffprobe-based deep checks below are skipped gracefully on the host
# and rely on the API's own scene_details/audio_used_scene_count metadata
# instead, which is itself real proof (computed from the actual render, not
# guessed). For the full ffprobe-backed verification, copy this script into
# the backend container and run it from there with the default SMOKE_DATA_DIR
# (leave it unset -- the container's own cwd is /app, so the default relative
# "data" already resolves correctly to /app/data; explicitly passing
# SMOKE_DATA_DIR=/app/data through a Git-Bash-wrapped `docker compose exec
# -e ...` is actually dangerous on Windows, since Git Bash silently mangles
# a bare leading "/app/..." argument into an MSYS path like
# "C:/Program Files/Git/app/data" -- this was hit and confirmed during this
# fix pack's own testing, see docs/DECISION_LOG.md 2026-06-28 entry):
#   docker compose cp scripts/test_audio_generate_all_and_video_integration.py backend:/app/t.py
#   docker compose exec -T backend python3 t.py
HAVE_FFPROBE = shutil.which("ffprobe") is not None and shutil.which("ffmpeg") is not None

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def request(method: str, path: str, body: dict | None = None, timeout: int = 30) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def request_raw(method: str, path: str) -> tuple[int, bytes]:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method=method)
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


def make_scene(scene_id: str, duration: int = 8) -> dict:
    return {
        "scene_id": scene_id,
        "title_ar": f"مشهد {scene_id}",
        "narration_ar": "نص قصير جداً للاختبار فقط.",
        "visual_description_ar": "وصف بصري للاختبار.",
        "image_prompt_en": "a simple test scene",
        "duration_seconds": duration,
    }


def create_test_project(title: str, scene_count: int, attach_images: bool) -> tuple[str, Path, list[dict]]:
    status, body = request(
        "POST",
        "/api/projects",
        {
            "title": title,
            "original_story": "",
            "improved_story": "",
            "scenes": [make_scene(f"{i:02d}") for i in range(1, scene_count + 1)],
        },
    )
    check(f"[{title}] create test project returns 200", status == 200)
    project = body["data"]
    project_id = project["project_id"]
    project_dir = DATA_DIR / "projects" / project_id
    scenes = project["scenes"]

    if attach_images:
        images_dir = project_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        for scene in scenes:
            (images_dir / f"scene_{scene['scene_id']}.png").write_bytes(TINY_PNG)
            scene["image_format"] = "png"
            scene["image_bytes"] = len(TINY_PNG)
            scene["image_width"] = 1
            scene["image_height"] = 1
        status, _ = request("PUT", f"/api/projects/{project_id}", {"scenes": scenes})
        check(f"[{title}] attach synthetic images returns 200", status == 200)

    return project_id, project_dir, scenes


def wait_for_terminal(job_id: str, max_wait_seconds: int = 90) -> dict:
    deadline = time.time() + max_wait_seconds
    last_job: dict = {}
    while time.time() < deadline:
        status, body = request("GET", f"/api/jobs/{job_id}")
        check("GET /api/jobs/{job_id} returns 200", status == 200)
        last_job = body["data"]
        if last_job["status"] in ("done", "failed", "cancelled"):
            return last_job
        time.sleep(1.0)
    check(f"job {job_id} reached a terminal status within {max_wait_seconds}s", False)
    return last_job


def is_real_wav(data: bytes) -> bool:
    return len(data) > 44 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"


# ── Test 1: sync generate-all persistence survives a reload ────────────────


def test_generate_all_sync_persists_and_survives_reload() -> None:
    project_id, project_dir, scenes = create_test_project("Audio Test Sync (throwaway)", 3, attach_images=False)
    try:
        status, body = request("POST", f"/api/projects/{project_id}/tts/generate-all", timeout=120)
        check("[sync] generate-all returns 200", status == 200)
        data = body["data"]
        check("[sync] generated count == 3", len(data["generated"]) == 3)
        check("[sync] failed count == 0", len(data["failed"]) == 0)

        status, body = request("GET", f"/api/projects/{project_id}/audio")
        scenes_audio = body["data"]["scenes"]
        count1 = sum(1 for s in scenes_audio if s["has_audio"])
        check("[sync] GET /audio reports 3/3 right after generation", count1 == 3)

        # Simulate a reload: a brand-new GET, no shared in-memory state.
        status, body = request("GET", f"/api/projects/{project_id}/audio")
        scenes_audio2 = body["data"]["scenes"]
        count2 = sum(1 for s in scenes_audio2 if s["has_audio"])
        check("[sync] GET /audio still reports 3/3 after a second independent read (reload)", count2 == 3)

        for scene in scenes_audio2:
            status, raw = request_raw("GET", scene["url"])
            check(f"[sync] scene {scene['scene_id']} audio file downloads with 200", status == 200)
            check(f"[sync] scene {scene['scene_id']} audio is a real non-empty WAV file", is_real_wav(raw))

        print(f"[INFO] sync_generate_all_count_after_reload={count2}/3")
    finally:
        request("DELETE", f"/api/projects/{project_id}")
        shutil.rmtree(project_dir, ignore_errors=True)


# ── Test 2: job-based generate-all persistence survives a reload ───────────


def test_generate_all_job_persists_and_survives_reload() -> None:
    project_id, project_dir, scenes = create_test_project("Audio Test Job (throwaway)", 3, attach_images=False)
    try:
        status, body = request("POST", f"/api/projects/{project_id}/tts/generate-all/jobs")
        check("[job] generate-all/jobs returns 200", status == 200)
        job_id = body["data"]["job_id"]

        final_job = wait_for_terminal(job_id)
        check("[job] job finished with status=done", final_job["status"] == "done")
        summary = final_job.get("result_summary") or {}
        check("[job] result_summary generated count == 3", len(summary.get("generated", [])) == 3)

        status, body = request("GET", f"/api/projects/{project_id}/audio")
        count = sum(1 for s in body["data"]["scenes"] if s["has_audio"])
        check("[job] GET /audio reports 3/3 right after job completion", count == 3)

        status, body = request("GET", f"/api/projects/{project_id}/audio")
        count2 = sum(1 for s in body["data"]["scenes"] if s["has_audio"])
        check("[job] GET /audio still reports 3/3 after a second independent read (reload)", count2 == 3)
        print(f"[INFO] job_generate_all_count_after_reload={count2}/3")
    finally:
        request("DELETE", f"/api/projects/{project_id}")
        shutil.rmtree(project_dir, ignore_errors=True)


# ── Test 3: video actually uses every scene's saved audio ───────────────────


def test_video_uses_all_scene_audio() -> None:
    project_id, project_dir, scenes = create_test_project("Video Audio Test (throwaway)", 3, attach_images=True)
    try:
        status, body = request("POST", f"/api/projects/{project_id}/tts/generate-all", timeout=120)
        check("[video-all-audio] generate-all returns 200", status == 200)
        check("[video-all-audio] generated count == 3", len(body["data"]["generated"]) == 3)

        status, body = request("POST", f"/api/projects/{project_id}/video/render/jobs")
        check("[video-all-audio] render job created", status == 200)
        final_job = wait_for_terminal(body["data"]["job_id"])
        check("[video-all-audio] render job finished with status=done", final_job["status"] == "done")
        metadata = final_job.get("result_summary") or {}

        details = {d["scene_id"]: d for d in metadata.get("scene_details", [])}
        check("[video-all-audio] scene_details present for all 3 scenes", len(details) == 3)
        check(
            "[video-all-audio] every scene has audio_used=true, duration_source=audio",
            all(d["audio_used"] is True and d["duration_source"] == "audio" for d in details.values()),
        )
        check(
            "[video-all-audio] audio_used_scene_count == 3",
            metadata.get("audio_used_scene_count") == 3,
        )

        video_path = project_dir / "video" / "final_story.mp4"
        check("[video-all-audio] rendered MP4 exists on disk", video_path.exists())
        if HAVE_FFPROBE:
            ffprobe_audio = _ffprobe_has_audio_and_duration(video_path)
            check("[video-all-audio] final MP4 has an audio stream", ffprobe_audio["has_audio"])
            check(
                f"[video-all-audio] real measured duration={ffprobe_audio['duration']:.2f}s "
                f"matches reported duration_seconds={metadata.get('duration_seconds')}s within 1.5s",
                abs(ffprobe_audio["duration"] - metadata.get("duration_seconds", -999)) < 1.5,
            )
            print(f"[INFO] all_audio_video_duration={ffprobe_audio['duration']:.1f}s")
        else:
            print("[SKIP] ffprobe not on this host's PATH -- relying on scene_details metadata above instead.")
        print(f"[INFO] reported_duration={metadata.get('duration_seconds')}s scene_details={list(details.values())}")
    finally:
        request("DELETE", f"/api/projects/{project_id}")
        shutil.rmtree(project_dir, ignore_errors=True)


# ── Test 4: mixed audio (some scenes have it, one doesn't) still works ──────


def test_video_with_missing_audio_on_one_scene() -> None:
    """The exact failure mode this fix pack targets: scenes 1 and 3 have
    real saved audio, scene 2 has none. Before the format-normalization fix,
    this produced a final video whose audio was desynced/effectively broken
    for the *whole clip past* the missing-audio segment -- not just scene 2's
    own portion, and scene 3's real audio was lost entirely. A weaker test
    that only checks "a silence window exists somewhere" would have given a
    false PASS on the broken version too (it had a silence window -- it just
    never ended). This test checks the window's *position* and that scene 3's
    audio is actually still there afterward, which the broken version fails."""
    project_id, project_dir, scenes = create_test_project("Video Missing Audio Test (throwaway)", 3, attach_images=True)
    try:
        for scene_id in ("01", "03"):
            status, body = request(
                "POST", f"/api/projects/{project_id}/tts/scenes/{scene_id}/generate", timeout=60
            )
            check(f"[mixed-audio] generate scene {scene_id} audio returns 200", status == 200)

        status, body = request("GET", f"/api/projects/{project_id}/audio")
        scenes_audio = {s["scene_id"]: s for s in body["data"]["scenes"]}
        check("[mixed-audio] scene 01 has audio", scenes_audio["01"]["has_audio"] is True)
        check("[mixed-audio] scene 02 has NO audio (as set up)", scenes_audio["02"]["has_audio"] is False)
        check("[mixed-audio] scene 03 has audio", scenes_audio["03"]["has_audio"] is True)

        # Exact expected timeline, computed from the real saved WAV durations
        # (not guessed) -- scene 2 has no audio, so it falls back to its
        # duration_seconds estimate (8s, set by make_scene()).
        audio1_seconds = _download_wav_duration_seconds(scenes_audio["01"]["url"])
        audio3_seconds = _download_wav_duration_seconds(scenes_audio["03"]["url"])
        scene2_duration_seconds = 8.0
        expected_scene2_start = audio1_seconds
        expected_scene2_end = audio1_seconds + scene2_duration_seconds
        expected_total = audio1_seconds + scene2_duration_seconds + audio3_seconds
        print(
            f"[INFO] expected_timeline audio1={audio1_seconds:.2f}s "
            f"scene2_silent={scene2_duration_seconds:.2f}s audio3={audio3_seconds:.2f}s "
            f"total={expected_total:.2f}s"
        )

        status, body = request("POST", f"/api/projects/{project_id}/video/render/jobs")
        check("[mixed-audio] render job created", status == 200)
        final_job = wait_for_terminal(body["data"]["job_id"])
        check("[mixed-audio] render job finished with status=done (not failed)", final_job["status"] == "done")
        metadata = final_job.get("result_summary") or {}

        details = {d["scene_id"]: d for d in metadata.get("scene_details", [])}
        check("[mixed-audio] scene 01 metadata: audio_used=true, duration_source=audio", details["01"]["audio_used"] is True and details["01"]["duration_source"] == "audio")
        check("[mixed-audio] scene 02 metadata: audio_used=false, duration_source=scene_duration, silent_audio_inserted=true", details["02"]["audio_used"] is False and details["02"]["duration_source"] == "scene_duration" and details["02"]["silent_audio_inserted"] is True)
        check("[mixed-audio] scene 03 metadata: audio_used=true, duration_source=audio", details["03"]["audio_used"] is True and details["03"]["duration_source"] == "audio")
        check("[mixed-audio] all scenes normalized to the same audio format", len({d["normalized_audio_format"] for d in details.values()}) == 1)
        check("[mixed-audio] all 3 scenes included (none skipped)", len(metadata.get("included_scenes", [])) == 3)
        check("[mixed-audio] audio_used_scene_count == 2", metadata.get("audio_used_scene_count") == 2)
        check(
            f"[mixed-audio] reported duration_seconds={metadata.get('duration_seconds')} "
            f"close to expected_total={expected_total:.1f}s",
            abs(metadata.get("duration_seconds", -999) - expected_total) < 1.5,
        )

        video_path = project_dir / "video" / "final_story.mp4"
        if HAVE_FFPROBE:
            ffprobe_audio = _ffprobe_has_audio_and_duration(video_path)
            check(
                "[mixed-audio] final MP4 still has a consistent audio stream despite one scene missing audio",
                ffprobe_audio["has_audio"],
            )
            check(
                f"[mixed-audio] real measured MP4 duration={ffprobe_audio['duration']:.2f}s "
                f"matches expected_total={expected_total:.2f}s within 1.5s "
                "(the broken version measured ~33% longer than expected)",
                abs(ffprobe_audio["duration"] - expected_total) < 1.5,
            )

            silence_windows = _ffprobe_silence_windows(video_path)
            check(
                "[mixed-audio] exactly one silence window detected (scene 2's silent track), not the whole tail desynced",
                len(silence_windows) == 1,
            )
            if silence_windows:
                silence_start, silence_end = silence_windows[0]
                check(
                    f"[mixed-audio] silence starts at scene 2's start (~{expected_scene2_start:.2f}s), measured {silence_start:.2f}s",
                    abs(silence_start - expected_scene2_start) < 0.75,
                )
                check(
                    f"[mixed-audio] silence ends before scene 3 starts (~{expected_scene2_end:.2f}s), measured {silence_end:.2f}s "
                    "-- the broken version never ended this window at all",
                    silence_end < expected_scene2_end + 0.75 and silence_end > expected_scene2_start,
                )

            scene3_volume = _ffprobe_mean_volume_db(video_path, start=expected_scene2_end + 0.3, duration=max(0.5, audio3_seconds - 0.5))
            check(
                f"[mixed-audio] scene 3's audio is actually audible after the silent section "
                f"(mean_volume={scene3_volume}dB, not near-silent) -- proves audio after the gap is NOT lost",
                scene3_volume is not None and scene3_volume > -50,
            )
            print(f"[INFO] mixed_audio_silence_windows={silence_windows} scene3_mean_volume_db={scene3_volume}")
        else:
            print("[SKIP] ffprobe not on this host's PATH -- relying on duration/scene_details metadata above instead.")
        print(f"[INFO] scene_details={list(details.values())}")
    finally:
        request("DELETE", f"/api/projects/{project_id}")
        shutil.rmtree(project_dir, ignore_errors=True)


def _download_wav_duration_seconds(url_path: str) -> float:
    status, raw = request_raw("GET", url_path)
    check(f"[mixed-audio] download {url_path} for exact duration measurement returns 200", status == 200)
    with wave.open(BytesIO(raw), "rb") as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        return frames / float(rate)


def _ffprobe_has_audio_and_duration(path: Path) -> dict:
    import subprocess

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=15, check=False,
    )
    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=15, check=False,
    )
    return {
        "has_audio": probe.returncode == 0 and bool(probe.stdout.strip()),
        "duration": float(dur.stdout.strip()) if dur.stdout.strip() else 0.0,
    }


def _ffprobe_silence_windows(path: Path) -> list[tuple[float, float]]:
    """Returns [(start, end), ...] for every detected silence window -- not
    just start times, so a window that never ends (the original bug, where
    silence swallowed the rest of the video) is distinguishable from one that
    closes normally."""
    import re
    import subprocess

    result = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af", "silencedetect=noise=-30dB:d=0.5", "-f", "null", "-"],
        capture_output=True, text=True, timeout=30, check=False,
    )
    starts = [float(s) for s in re.findall(r"silence_start:\s*([\d.]+)", result.stderr)]
    ends = [float(e) for e in re.findall(r"silence_end:\s*([\d.]+)", result.stderr)]
    return list(zip(starts, ends))


def _ffprobe_mean_volume_db(path: Path, start: float, duration: float) -> float | None:
    import re
    import subprocess

    result = subprocess.run(
        ["ffmpeg", "-ss", f"{start:.3f}", "-i", str(path), "-t", f"{duration:.3f}", "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, timeout=30, check=False,
    )
    match = re.search(r"mean_volume:\s*(-?[\d.]+)\s*dB", result.stderr)
    return float(match.group(1)) if match else None


def main() -> None:
    status, health = request("GET", "/api/tts/health")
    if status != 200 or not health.get("data", {}).get("configured") or not health.get("data", {}).get("remote_ok"):
        print("[SKIP] TTS worker not reachable from this host -- cannot run the real audio persistence test.")
        return

    test_generate_all_sync_persists_and_survives_reload()
    test_generate_all_job_persists_and_survives_reload()
    test_video_uses_all_scene_audio()
    test_video_with_missing_audio_on_one_scene()
    print("Audio generate-all and video integration test passed.")


if __name__ == "__main__":
    main()
