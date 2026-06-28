from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response

from app.config import Settings, get_settings
from app.jobs import JobStore, get_job_store, now_iso
from app.schemas import ApiEnvelope
from app.storage import ProjectStorage

router = APIRouter(tags=["video"])

# MVP target: matches the image pipeline's fixed 768x768 output (Phase 2.1/2.2).
RENDER_WIDTH = 768
RENDER_HEIGHT = 768
SEGMENT_TIMEOUT_SECONDS = 60
CONCAT_TIMEOUT_SECONDS = 120
KEN_BURNS_FPS = 25
KEN_BURNS_MAX_ZOOM = 1.15
KEN_BURNS_ZOOM_STEP = 0.0008
MAX_FADE_SECONDS = 0.5


def _build_segment_video_filter(video_mode: str, video_transition: str, duration: float) -> str:
    """ffmpeg-only video filter chain for one scene segment.

    `ken_burns` is a slow zoom-in pan via the `zoompan` filter (Milestone E) --
    not AI motion, just a deterministic ffmpeg effect on the existing static
    image, capped at 1.15x zoom so it stays subtle. `fade` is a short
    fade-in/fade-out *within* each segment (not a true crossfade between
    segments -- the pipeline still concatenates segments with the lossless
    `-c copy` demuxer, so a real crossfade would require re-encoding the
    whole concat step). This is a deliberate low-risk simplification: it
    softens hard cuts without touching the duration-sync guarantee from the
    Milestone 0 fix.
    """
    filters: list[str] = []
    if video_mode == "ken_burns":
        total_frames = max(1, round(duration * KEN_BURNS_FPS))
        zoom_expr = f"min(zoom+{KEN_BURNS_ZOOM_STEP},{KEN_BURNS_MAX_ZOOM})"
        filters.append(
            f"zoompan=z='{zoom_expr}':d={total_frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={RENDER_WIDTH}x{RENDER_HEIGHT}:fps={KEN_BURNS_FPS}"
        )
    else:
        filters.append(f"scale={RENDER_WIDTH}:{RENDER_HEIGHT}")

    if video_transition == "fade" and duration > 0:
        fade_duration = min(MAX_FADE_SECONDS, duration / 4)
        if fade_duration > 0:
            fade_out_start = max(0.0, duration - fade_duration)
            filters.append(f"fade=t=in:st=0:d={fade_duration:.3f}")
            filters.append(f"fade=t=out:st={fade_out_start:.3f}:d={fade_duration:.3f}")

    return ",".join(filters)


def get_storage(settings: Settings = Depends(get_settings)) -> ProjectStorage:
    return ProjectStorage(settings)


def get_store(settings: Settings = Depends(get_settings)) -> JobStore:
    return get_job_store(settings.data_path)


class FfmpegError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class VideoNoContentError(RuntimeError):
    """Project has no scenes, or no scene has a usable saved image yet."""


def _run_ffmpeg(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise FfmpegError("ffmpeg is not available in the backend image.", status_code=503) from exc
    except subprocess.TimeoutExpired as exc:
        raise FfmpegError("ffmpeg timed out.", status_code=502) from exc


def _final_video_has_audio_stream(path: Path) -> bool:
    """ffprobe check used only as a post-render safety net (Hamza fix pack,
    2026-06-28): proves the rendered MP4 actually contains an audio stream
    instead of trusting that ffmpeg's exit code alone means the result is
    correct -- a stream-layout mismatch between concatenated segments can
    silently produce a video with no usable audio even when ffmpeg exits 0."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        return False


def _render_video_for_project(
    project_id: str,
    storage: ProjectStorage,
    on_progress: Callable[[int, int], None] | None = None,
) -> dict:
    """Shared render core used by both the synchronous endpoint and the
    job-based endpoint below. Raises FileNotFoundError (no project),
    VideoNoContentError (no scenes / no renderable images), or FfmpegError
    (binary missing, timeout, or non-zero exit) -- callers translate these
    into either an HTTPException (sync path) or a failed job record (job
    path), so the actual ffmpeg logic only lives here.
    """
    project = storage.get_project(project_id)

    if not project.scenes:
        raise VideoNoContentError("Project has no scenes to render.")

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
    scene_details: list[dict] = []
    any_scene_has_audio = False
    total_scenes = len(project.scenes)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        segment_paths: list[Path] = []

        for index, scene in enumerate(project.scenes, start=1):
            if on_progress:
                on_progress(index, total_scenes)

            if not scene.image_format:
                skipped.append({"scene_id": scene.scene_id, "reason": "no saved image for this scene"})
                scene_details.append({
                    "scene_id": scene.scene_id, "image_used": False, "audio_used": False,
                    "audio_path_exists": False, "duration_source": None, "duration_seconds": None,
                    "skip_reason": "no saved image for this scene",
                })
                continue
            image_path = images_dir / f"scene_{scene.scene_id}.{scene.image_format}"
            if not image_path.exists():
                skipped.append({"scene_id": scene.scene_id, "reason": "image file missing on disk"})
                scene_details.append({
                    "scene_id": scene.scene_id, "image_used": False, "audio_used": False,
                    "audio_path_exists": False, "duration_source": None, "duration_seconds": None,
                    "skip_reason": "image file missing on disk",
                })
                continue

            audio_path = None
            audio_path_exists = False
            if scene.audio_format:
                candidate = audio_dir / f"scene_{scene.scene_id}.{scene.audio_format}"
                if candidate.exists():
                    audio_path = candidate
                    audio_path_exists = True

            # Use the scene's real saved-audio duration when present (Issue 2
            # fix: previously always used the fixed duration_seconds estimate,
            # so a video could run noticeably shorter than its own narration
            # and cut audio off mid-sentence). Falls back to duration_seconds
            # only when there is no saved audio for this scene.
            segment_duration = scene_durations[scene.scene_id]
            duration_source = "audio" if audio_path is not None else "scene_duration"

            video_filter = _build_segment_video_filter(
                project.video_mode, project.video_transition, segment_duration
            )
            segment_path = tmp_path / f"segment_{scene.scene_id}.mp4"
            cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(image_path)]
            if audio_path is not None:
                cmd += ["-i", str(audio_path)]
                any_scene_has_audio = True
            else:
                # A scene with no saved audio still gets a silent audio track
                # of the same duration, instead of "-an" (no audio stream at
                # all). The concat step below uses "-c copy", which requires
                # every segment to share the same stream layout -- mixing
                # audio-having and audio-less ("-an") segments was found
                # (2026-06-28 fix pack, verified with ffprobe/silencedetect)
                # to desync or drop audio for the *entire* rest of the
                # concatenated video, not just the one scene missing it. A
                # silent track keeps every segment's stream layout identical.
                cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
            cmd += [
                "-t", f"{segment_duration:.3f}",
                "-vf", video_filter,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
            ]
            cmd.append(str(segment_path))

            result = _run_ffmpeg(cmd, SEGMENT_TIMEOUT_SECONDS)
            if result.returncode != 0 or not segment_path.exists():
                skipped.append({"scene_id": scene.scene_id, "reason": "ffmpeg segment render failed"})
                scene_details.append({
                    "scene_id": scene.scene_id, "image_used": True, "audio_used": False,
                    "audio_path_exists": audio_path_exists, "duration_source": duration_source,
                    "duration_seconds": segment_duration, "skip_reason": "ffmpeg segment render failed",
                })
                continue

            segment_paths.append(segment_path)
            included.append(scene.scene_id)
            included_durations.append(segment_duration)
            scene_details.append({
                "scene_id": scene.scene_id, "image_used": True, "audio_used": audio_path is not None,
                "audio_path_exists": audio_path_exists, "duration_source": duration_source,
                "duration_seconds": segment_duration, "skip_reason": None,
            })

        if not segment_paths:
            raise VideoNoContentError(
                "No scene has a saved image yet -- generate at least one scene image first."
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
            raise FfmpegError("ffmpeg concat step failed.")

        # Post-render safety net (Milestone B.4): every segment always has an
        # audio stream now (real or silent), so the final file must have one
        # too -- if it doesn't despite at least one scene having real saved
        # audio, treat that as a clear render failure instead of silently
        # shipping a video with no usable audio.
        if any_scene_has_audio and not _final_video_has_audio_stream(final_path):
            raise FfmpegError("الفيديو النهائي لا يحتوي على مسار صوت رغم وجود صوت محفوظ لبعض المشاهد.")

    total_duration = round(sum(included_durations))
    metadata = {
        "rendered_at": datetime.now(timezone.utc).isoformat(),
        "included_scenes": included,
        "skipped_scenes": skipped,
        "scene_details": scene_details,
        "audio_used_scene_count": sum(1 for d in scene_details if d["audio_used"]),
        "duration_seconds": total_duration,
        "video_bytes": final_path.stat().st_size,
        "video_mode": project.video_mode,
        "video_transition": project.video_transition,
    }
    storage.save_video_metadata(project_id, metadata)
    return metadata


def _run_render_video_job(job_store: JobStore, job_id: str, project_id: str, storage: ProjectStorage) -> None:
    job_store.update(
        job_id, status="running", started_at=now_iso(),
        message_ar="جاري تجميع الفيديو من الصور والصوت المحفوظ...",
    )
    try:
        def on_progress(index: int, total: int) -> None:
            job_store.update(
                job_id,
                current_step=index,
                total_steps=total,
                completed_steps=index - 1,
                message_ar=f"جاري تجميع مشهد {index} من {total} في الفيديو...",
            )

        metadata = _render_video_for_project(project_id, storage, on_progress=on_progress)
        total = len(metadata.get("included_scenes", [])) + len(metadata.get("skipped_scenes", []))
        job_store.update(
            job_id,
            status="done",
            current_step=total,
            completed_steps=total,
            finished_at=now_iso(),
            message_ar=f"تم تجميع الفيديو بمدة {metadata['duration_seconds']} ثانية تقريباً.",
            affected_scene_ids=metadata.get("included_scenes", []),
            result_summary=metadata,
        )
    except FileNotFoundError as exc:
        job_store.update(
            job_id, status="failed", finished_at=now_iso(), safe_error_ar=str(exc), message_ar="فشل تجميع الفيديو."
        )
    except VideoNoContentError as exc:
        job_store.update(
            job_id, status="failed", finished_at=now_iso(), safe_error_ar=str(exc), message_ar="فشل تجميع الفيديو."
        )
    except FfmpegError as exc:
        job_store.update(
            job_id, status="failed", finished_at=now_iso(), safe_error_ar=str(exc), message_ar="فشل تجميع الفيديو."
        )
    except Exception:
        job_store.update(
            job_id,
            status="failed",
            finished_at=now_iso(),
            safe_error_ar="حدث خطأ غير متوقع أثناء تجميع الفيديو.",
            message_ar="فشل تجميع الفيديو.",
        )


@router.post("/api/projects/{project_id}/video/render", response_model=ApiEnvelope)
def render_project_video(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    try:
        metadata = _render_video_for_project(project_id, storage)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VideoNoContentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FfmpegError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return ApiEnvelope(data=metadata, meta={"provider": "ffmpeg"})


@router.post("/api/projects/{project_id}/video/render/jobs", response_model=ApiEnvelope)
def render_project_video_job(
    project_id: str,
    background_tasks: BackgroundTasks,
    storage: ProjectStorage = Depends(get_storage),
    store: JobStore = Depends(get_store),
) -> ApiEnvelope:
    """Job-based variant of /video/render -- returns a job_id immediately so
    the UI can poll instead of blocking on the whole ffmpeg render+concat run."""
    try:
        project = storage.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not project.scenes:
        raise HTTPException(status_code=422, detail="Project has no scenes to render.")

    job = store.create(
        project_id, "video_render", total_steps=len(project.scenes), message_ar="في قائمة الانتظار..."
    )
    background_tasks.add_task(_run_render_video_job, store, job.job_id, project_id, storage)
    return ApiEnvelope(data=job.to_dict(), meta={"provider": "ffmpeg"})


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
        "scene_details": metadata.get("scene_details", []),
        "audio_used_scene_count": metadata.get("audio_used_scene_count", 0),
        "video_mode": metadata.get("video_mode", "static"),
        "video_transition": metadata.get("video_transition", "none"),
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
