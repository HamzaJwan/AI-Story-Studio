"""Regression test for the 2026-06-28 "Voice Expansion Lab" fix pack.

Hamza's ask: add real, working narrator voice choices (not just names in the
UI) and make sure a chosen voice actually flows into generated audio and the
final video, while keeping Arabic Kareem as the safe default and never
displaying a voice that doesn't actually work.

Forensic finding (see docs/DECISION_LOG.md, 2026-06-28 "Voice Expansion Lab"
entry): no second safe Arabic voice is available right now within the
project's safety rules --
  - Piper's own official voice catalog has exactly one Arabic speaker
    ("kareem", ar_JO) in two quality tiers of the SAME speaker.
  - The AllTalk service reachable on the AI Server exposes celebrity-named
    reference samples (forbidden outright) and unattributed generic samples
    with no documented consent (AllTalk is voice CLONING by design, so those
    stay Deferred per the safety rules).
  - SILMA is explicitly blocked on this deployment (stalled model download).
So this test suite proves the *infrastructure* is real and end-to-end
correct for whatever voice IS available today (Kareem), not that a second
voice exists -- /api/tts/voices must never claim a voice works without
checking, voice_id must actually steer generation (not be cosmetic), and an
explicitly-unavailable voice_id must fail loudly rather than silently
substitute a different voice the user didn't ask for.

Uses the REAL TTS worker (confirmed reachable via `GET /api/tts/health`).
Skips gracefully if the TTS worker is not reachable. Always deletes its test
project. Never prints narration/audio content.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("SMOKE_BASE_URL", "http://localhost:8810")
DATA_DIR = Path(os.environ.get("SMOKE_DATA_DIR", "data"))


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


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        sys.exit(1)


def make_scene(scene_id: str, duration: int = 6) -> dict:
    return {
        "scene_id": scene_id,
        "title_ar": f"مشهد {scene_id}",
        "narration_ar": "نص قصير جداً للاختبار فقط.",
        "visual_description_ar": "وصف بصري للاختبار.",
        "image_prompt_en": "a simple test scene",
        "duration_seconds": duration,
    }


def create_test_project(title: str, scene_count: int) -> tuple[str, Path, list[dict]]:
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
    return project_id, project_dir, project["scenes"]


REQUIRED_VOICE_FIELDS = {
    "voice_id",
    "display_name_ar",
    "gender",
    "language",
    "engine",
    "quality_label",
    "available",
    "notes_ar",
}


# ── Test 1: voice catalog reflects real discovery, not a static guess ──────


def test_voice_catalog() -> None:
    status, body = request("GET", "/api/tts/voices")
    check("[catalog] GET /api/tts/voices returns 200", status == 200)
    data = body["data"]
    voices = data["voices"]

    check("[catalog] at least one voice is returned", len(voices) >= 1)
    for voice in voices:
        check(
            f"[catalog] voice {voice.get('voice_id')} has all required fields",
            REQUIRED_VOICE_FIELDS.issubset(voice.keys()),
        )

    kareem = next((v for v in voices if v["voice_id"] == "ar_JO-kareem-medium"), None)
    check("[catalog] Arabic Kareem is present in the catalog", kareem is not None)
    check("[catalog] Arabic Kareem is marked available (worker is reachable)", kareem is not None and kareem["available"])
    check("[catalog] Arabic Kareem is the default voice", kareem is not None and kareem.get("default") is True)
    check("[catalog] Arabic Kareem is male", kareem is not None and kareem["gender"] == "male")
    check("[catalog] Arabic Kareem is not flagged experimental", kareem is not None and kareem["experimental"] is False)

    # No voice may be reported available unless the live worker health check
    # actually backs it up -- this is what makes the catalog "real discovery"
    # instead of a frozen list that can silently drift from reality.
    status, health_body = request("GET", "/api/tts/health")
    remote_ok = health_body["data"].get("remote_ok")
    if not remote_ok:
        check("[catalog] no voice is reported available when the worker is unreachable", all(not v["available"] for v in voices))

    check(
        "[catalog] single_voice_available flag matches the actual available count",
        data["single_voice_available"] == (sum(1 for v in voices if v["available"]) <= 1),
    )
    check("[catalog] default_voice_id matches Arabic Kareem", data["default_voice_id"] == "ar_JO-kareem-medium")


# ── Test 2: generation with an explicitly selected voice actually uses it ──


def test_generation_records_selected_voice() -> None:
    project_id, project_dir, scenes = create_test_project("Voice Selection Test (throwaway)", 2)
    try:
        status, body = request(
            "POST", f"/api/projects/{project_id}/tts/generate-all?voice_id=ar_JO-kareem-medium", timeout=120
        )
        check("[voice-select] generate-all with explicit voice_id returns 200", status == 200)
        data = body["data"]
        check("[voice-select] generated count == 2", len(data["generated"]) == 2)
        check("[voice-select] failed count == 0", len(data["failed"]) == 0)

        status, body = request("GET", f"/api/projects/{project_id}/audio")
        scenes_audio = body["data"]["scenes"]
        for scene in scenes_audio:
            check(f"[voice-select] scene {scene['scene_id']} has audio", scene["has_audio"])
            check(
                f"[voice-select] scene {scene['scene_id']} metadata records the requested voice_id "
                f"(got {scene.get('audio_voice_id')!r})",
                scene["audio_voice_id"] == "ar_JO-kareem-medium",
            )
            check(
                f"[voice-select] scene {scene['scene_id']} metadata records the engine (got {scene.get('audio_engine')!r})",
                scene["audio_engine"] == "piper",
            )

        # Reload independently (new GET, no shared in-memory state) -- proves
        # voice_id/engine survive exactly like the audio file itself does.
        status, body = request("GET", f"/api/projects/{project_id}/audio")
        scenes_audio2 = body["data"]["scenes"]
        check(
            "[voice-select] voice_id metadata survives an independent reload",
            all(s["audio_voice_id"] == "ar_JO-kareem-medium" for s in scenes_audio2),
        )
    finally:
        request("DELETE", f"/api/projects/{project_id}")
        shutil.rmtree(project_dir, ignore_errors=True)


# ── Test 3: an explicitly unavailable/unknown voice fails honestly ────────


def test_unknown_voice_id_fails_instead_of_silently_substituting() -> None:
    project_id, project_dir, scenes = create_test_project("Voice Selection Unknown Test (throwaway)", 1)
    try:
        status, body = request(
            "POST", f"/api/projects/{project_id}/tts/generate-all?voice_id=does-not-exist-female-voice", timeout=60
        )
        check("[voice-unknown] generate-all returns 200 (request itself succeeds)", status == 200)
        data = body["data"]
        check("[voice-unknown] generated count == 0 (nothing was silently generated with a different voice)", len(data["generated"]) == 0)
        check("[voice-unknown] failed count == 1", len(data["failed"]) == 1)

        status, body = request("GET", f"/api/projects/{project_id}/audio")
        scenes_audio = body["data"]["scenes"]
        check(
            "[voice-unknown] no audio was saved for the unknown-voice request",
            all(not s["has_audio"] for s in scenes_audio),
        )

        # The single-scene endpoint must reject the same way (502, not a
        # silent fallback to Kareem).
        status, body = request(
            "POST", f"/api/projects/{project_id}/tts/scenes/{scenes[0]['scene_id']}/generate?voice_id=does-not-exist-female-voice"
        )
        check("[voice-unknown] single-scene generate with unknown voice_id returns 502", status == 502)
    finally:
        request("DELETE", f"/api/projects/{project_id}")
        shutil.rmtree(project_dir, ignore_errors=True)


# ── Test 4: default voice (no voice_id given) still works -- regression ───


def test_default_voice_still_works_without_voice_id() -> None:
    project_id, project_dir, scenes = create_test_project("Voice Selection Default Test (throwaway)", 1)
    try:
        status, body = request(
            "POST", f"/api/projects/{project_id}/tts/scenes/{scenes[0]['scene_id']}/generate", timeout=60
        )
        check("[voice-default] single-scene generate with no voice_id returns 200", status == 200)

        status, body = request("GET", f"/api/projects/{project_id}/audio")
        scene_audio = body["data"]["scenes"][0]
        check("[voice-default] scene has audio", scene_audio["has_audio"])
        check(
            "[voice-default] defaults to Arabic Kareem when no voice_id is given",
            scene_audio["audio_voice_id"] == "ar_JO-kareem-medium",
        )
    finally:
        request("DELETE", f"/api/projects/{project_id}")
        shutil.rmtree(project_dir, ignore_errors=True)


def main() -> None:
    status, health = request("GET", "/api/tts/health")
    if status != 200 or not health.get("data", {}).get("configured") or not health.get("data", {}).get("remote_ok"):
        print("[SKIP] TTS worker not reachable from this host -- cannot run the real voice selection test.")
        return

    test_voice_catalog()
    test_generation_records_selected_voice()
    test_unknown_voice_id_fails_instead_of_silently_substituting()
    test_default_voice_still_works_without_voice_id()
    print("Voice selection test passed.")


if __name__ == "__main__":
    main()
