from __future__ import annotations

import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.config import Settings, get_settings
from app.schemas import ApiEnvelope
from app.storage import ProjectStorage

router = APIRouter(tags=["video"])

# MVP target: matches the image pipeline's fixed 768x768 output (Phase 2.1/2.2).
RENDER_WIDTH = 768
RENDER_HEIGHT = 768
SEGMENT_TIMEOUT_SECONDS = 60
CONCAT_TIMEOUT_SECONDS = 120


def get_storage(settings: Settings = Depends(get_settings)) -> ProjectStorage:
    return ProjectStorage(settings)


def _run_ffmpeg(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503, detail="ffmpeg is not available in the backend image."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=502, detail="ffmpeg timed out.") from exc


@router.post("/api/projects/{project_id}/video/render", response_model=ApiEnvelope)
def render_project_video(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    try:
        project = storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not project.scenes:
        raise HTTPException(status_code=422, detail="Project has no scenes to render.")

    images_dir = storage.project_images_dir(project_id)
    audio_dir = storage.project_audio_dir(project_id)
    video_dir = storage.project_video_dir(project_id)
    scene_durations = dict(zip(
        (scene.scene_id for scene in project.scenes),
        storage.get_scene_render_durations(project),
    ))

    included: list[str] = []
    included_durations: list[float] = []
    skipped: list[dict[str, str]] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        segment_paths: list[Path] = []

        for scene in project.scenes:
            if not scene.image_format:
                skipped.append({"scene_id": scene.scene_id, "reason": "no saved image for this scene"})
                continue
            image_path = images_dir / f"scene_{scene.scene_id}.{scene.image_format}"
            if not image_path.exists():
                skipped.append({"scene_id": scene.scene_id, "reason": "image file missing on disk"})
                continue

            audio_path = None
            if scene.audio_format:
                candidate = audio_dir / f"scene_{scene.scene_id}.{scene.audio_format}"
                if candidate.exists():
                    audio_path = candidate

            # Use the scene's real saved-audio duration when present (Issue 2
            # fix: previously always used the fixed duration_seconds estimate,
            # so a video could run noticeably shorter than its own narration
            # and cut audio off mid-sentence). Falls back to duration_seconds
            # only when there is no saved audio for this scene.
            segment_duration = scene_durations[scene.scene_id]

            segment_path = tmp_path / f"segment_{scene.scene_id}.mp4"
            cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(image_path)]
            if audio_path is not None:
                cmd += ["-i", str(audio_path)]
            cmd += [
                "-t", f"{segment_duration:.3f}",
                "-vf", f"scale={RENDER_WIDTH}:{RENDER_HEIGHT}",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
            ]
            if audio_path is not None:
                cmd += ["-c:a", "aac"]
            else:
                cmd += ["-an"]
            cmd.append(str(segment_path))

            result = _run_ffmpeg(cmd, SEGMENT_TIMEOUT_SECONDS)
            if result.returncode != 0 or not segment_path.exists():
                skipped.append({"scene_id": scene.scene_id, "reason": "ffmpeg segment render failed"})
                continue

            segment_paths.append(segment_path)
            included.append(scene.scene_id)
            included_durations.append(segment_duration)

        if not segment_paths:
            raise HTTPException(
                status_code=422,
                detail="No scene has a saved image yet -- generate at least one scene image first.",
            )

        concat_list = tmp_path / "concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{p.as_posix()}'" for p in segment_paths),
            encoding="utf-8",
        )

        final_path = video_dir / "final_story.mp4"
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy",
            str(final_path),
        ]
        result = _run_ffmpeg(concat_cmd, CONCAT_TIMEOUT_SECONDS)
        if result.returncode != 0 or not final_path.exists():
            raise HTTPException(status_code=502, detail="ffmpeg concat step failed.")

    total_duration = round(sum(included_durations))
    metadata = {
        "rendered_at": datetime.now(timezone.utc).isoformat(),
        "included_scenes": included,
        "skipped_scenes": skipped,
        "duration_seconds": total_duration,
        "video_bytes": final_path.stat().st_size,
    }
    storage.save_video_metadata(project_id, metadata)

    return ApiEnvelope(data=metadata, meta={"provider": "ffmpeg"})


@router.get("/api/projects/{project_id}/video", response_model=ApiEnvelope)
def get_project_video(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    try:
        storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    video_path = storage.get_video_path(project_id)
    metadata = storage.get_video_metadata(project_id) or {}
    data = {
        "project_id": project_id,
        "has_video": video_path is not None,
        "url": f"/api/projects/{project_id}/video/download" if video_path is not None else None,
        "duration_seconds": metadata.get("duration_seconds"),
        "video_bytes": metadata.get("video_bytes"),
        "rendered_at": metadata.get("rendered_at"),
        "included_scenes": metadata.get("included_scenes", []),
        "skipped_scenes": metadata.get("skipped_scenes", []),
    }
    return ApiEnvelope(data=data)


@router.get("/api/projects/{project_id}/video/download")
def download_project_video(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> Response:
    try:
        storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    video_path = storage.get_video_path(project_id)
    if video_path is None:
        raise HTTPException(status_code=404, detail="No rendered video for this project yet.")
    return Response(content=video_path.read_bytes(), media_type="video/mp4")
