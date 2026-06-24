from __future__ import annotations

import json
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/workspace")
DATA_DIR = ROOT / "data" / "jobs"
DATA_DIR.mkdir(parents=True, exist_ok=True)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.tts.silma_benchmark import (  # noqa: E402
    call_silma,
    convert_to_mp3,
    detect_device,
    find_reference_audio,
    find_reference_text,
    install_official_silma_reference,
    instantiate_tts,
)

_lock = threading.Lock()
_jobs: dict[str, dict] = {}


def _job_dir(job_id: str) -> Path:
    path = DATA_DIR / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save(job: dict) -> None:
    job_path = _job_dir(job["job_id"]) / "job.json"
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")


def create_job(text: str, voice_id: str | None, speed: float | None, fmt: str) -> dict:
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    job = {
        "job_id": job_id,
        "status": "queued",
        "text": text,
        "voice_id": voice_id,
        "speed": speed or 1.0,
        "format": fmt or "wav",
        "error": None,
        "files": [],
        "reference_voice_note": None,
        "created_at": now,
        "updated_at": now,
    }
    with _lock:
        _jobs[job_id] = job
    _save(job)
    threading.Thread(target=_run_job, args=(job_id,), daemon=True).start()
    return job


def get_job(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        if job:
            return dict(job)
    job_path = DATA_DIR / job_id / "job.json"
    if job_path.exists():
        return json.loads(job_path.read_text(encoding="utf-8"))
    return None


def _update(job_id: str, **fields) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.update(fields)
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        snapshot = dict(job)
    _save(snapshot)


def _run_job(job_id: str) -> None:
    job = get_job(job_id)
    if job is None:
        return
    _update(job_id, status="running")

    output_dir = _job_dir(job_id)
    output_wav = output_dir / "audio.wav"
    output_mp3 = output_dir / "audio.mp3"

    try:
        reference_audio = find_reference_audio(output_dir)
        ref_text = find_reference_text(reference_audio)
        reference_note = None

        if not reference_audio:
            official = install_official_silma_reference(output_dir)
            if official:
                reference_audio, ref_text = official
                reference_note = (
                    "Used SILMA's bundled official benchmark sample — testing only, "
                    "not an approved product voice. Set REF_AUDIO/REF_TEXT for a real run."
                )
            else:
                raise RuntimeError(
                    "NEEDS_REFERENCE: no permitted reference audio with matching text was found."
                )
        if reference_audio and not ref_text:
            raise RuntimeError(
                "NEEDS_REFERENCE: reference audio exists but no permitted reference text was found."
            )

        from silma_tts.api import SilmaTTS

        tts = instantiate_tts(SilmaTTS)
        call_silma(tts, job["text"], output_wav, reference_audio, ref_text, float(job["speed"]))

        files = [{"format": "wav", "path": str(output_wav), "bytes": output_wav.stat().st_size}]
        if job["format"] == "mp3" and convert_to_mp3(output_wav, output_mp3):
            files.append({"format": "mp3", "path": str(output_mp3), "bytes": output_mp3.stat().st_size})

        _update(job_id, status="done", files=files, reference_voice_note=reference_note)
    except Exception as exc:  # noqa: BLE001
        _update(job_id, status="failed", error=str(exc))
