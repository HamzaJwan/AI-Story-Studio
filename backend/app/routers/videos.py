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

# Fixed audio format every segment is normalized to before concat (fix pack,
# 2026-06-28, Codex HOLD). Root cause: real saved narration audio (Piper,
# 22050Hz mono) was passed into each segment's ffmpeg call with no explicit
# `-ar`/`-ac`, so AAC encoding kept its native 22050/mono layout, while the
# silent track for audio-less scenes was generated at 44100Hz stereo
# (`anullsrc`). ffmpeg's concat demuxer (`-c copy`) trusts that every input
# segment already shares one stream layout -- it does NOT reconcile differing
# sample rates/channel counts at concat time. The mismatch produced
# "Non-monotonic DTS" warnings and silence that never ended (a 3s scene
# rendered as 4.07s, with the next scene's real audio effectively lost).
# Forcing the same `-ar`/`-ac` (via output options, so ffmpeg's own resampler
# normalizes whatever the input actually is) on *every* segment -- real audio
# and silent alike -- makes every segment's audio stream byte-for-byte
# consistent, which is what `-c copy` concat actually requires.
NORMALIZED_AUDIO_SAMPLE_RATE = 48000
NORMALIZED_AUDIO_CHANNELS = 2
NORMALIZED_AUDIO_CODEC = "aac"


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


def _ffprobe_duration_seconds(path: Path) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return None


def _final_video_audio_stream_info(path: Path) -> dict | None:
    """ffprobe check used as a post-render safety net (Hamza fix pack,
    2026-06-28): proves the rendered MP4 actually contains a *single,
    consistent* audio stream instead of trusting that ffmpeg's exit code
    alone means the result is correct -- a stream-layout mismatch between
    concatenated segments can silently produce a video with broken/missing
    audio even when ffmpeg exits 0. Returns None if there is no audio stream
    at all, otherwise {"sample_rate": int, "channels": int}."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=sample_rate,channels", "-of", "csv=p=0",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        sample_rate_str, channels_str = result.stdout.strip().split(",")
        return {"sample_rate": int(sample_rate_str), "channels": int(channels_str)}
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


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
                    "silent_audio_inserted": False, "normalized_audio_format": None,
                    "audio_sample_rate": None, "audio_channels": None,
                })
                continue
            image_path = images_dir / f"scene_{scene.scene_id}.{scene.image_format}"
            if not image_path.exists():
                skipped.append({"scene_id": scene.scene_id, "reason": "image file missing on disk"})
                scene_details.append({
                    "scene_id": scene.scene_id, "image_used": False, "audio_used": False,
                    "audio_path_exists": False, "duration_source": None, "duration_seconds": None,
                    "skip_reason": "image file missing on disk",
                    "silent_audio_inserted": False, "normalized_audio_format": None,
                    "audio_sample_rate": None, "audio_channels": None,
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
            silent_audio_inserted = audio_path is None

            video_filter = _build_segment_video_filter(
                project.video_mode, project.video_transition, segment_duration
            )
            segment_path = tmp_path / f"segment_{scene.scene_id}.mp4"
            cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(image_path)]
            if audio_path is not None:
                # Real saved narration audio (Piper: 22050Hz mono) is fed in
                # at its native format -- the explicit "-ar"/"-ac" OUTPUT
                # options below force ffmpeg's own resampler to re-encode it
                # into the same fixed format every segment uses, instead of
                # passing it through to AAC at its native rate/channels.
                cmd += ["-i", str(audio_path)]
                any_scene_has_audio = True
            else:
                # A scene with no saved audio still gets a silent audio track
                # of the same duration and the same normalized format, instead
                # of "-an" (no audio stream at all) or a silent track at a
                # *different* format. The concat step below uses "-c copy",
                # which requires every segment's audio stream to be
                # byte-for-byte the same sample rate/channel layout/codec --
                # generating the silent track at anything other than the
                # exact normalized format reproduces the same "Non-monotonic
                # DTS" / silence-never-ends bug this fix pack addresses.
                cmd += [
                    "-f", "lavfi", "-i",
                    f"anullsrc=channel_layout=stereo:sample_rate={NORMALIZED_AUDIO_SAMPLE_RATE}",
                ]
            cmd += [
                "-t", f"{segment_duration:.3f}",
                "-vf", video_filter,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-c:a", NORMALIZED_AUDIO_CODEC,
                "-ar", str(NORMALIZED_AUDIO_SAMPLE_RATE),
                "-ac", str(NORMALIZED_AUDIO_CHANNELS),
            ]
            cmd.append(str(segment_path))

            result = _run_ffmpeg(cmd, SEGMENT_TIMEOUT_SECONDS)
            if result.returncode != 0 or not segment_path.exists():
                skipped.append({"scene_id": scene.scene_id, "reason": "ffmpeg segment render failed"})
                scene_details.append({
                    "scene_id": scene.scene_id, "image_used": True, "audio_used": False,
                    "audio_path_exists": audio_path_exists, "duration_source": duration_source,
                    "duration_seconds": segment_duration, "skip_reason": "ffmpeg segment render failed",
                    "silent_audio_inserted": silent_audio_inserted,
                    "normalized_audio_format": None,
                    "audio_sample_rate": None, "audio_channels": None,
                })
                continue

            segment_paths.append(segment_path)
            included.append(scene.scene_id)
            included_durations.append(segment_duration)
            scene_details.append({
                "scene_id": scene.scene_id, "image_used": True, "audio_used": audio_path is not None,
                "audio_path_exists": audio_path_exists, "duration_source": duration_source,
                "duration_seconds": segment_duration, "skip_reason": None,
                "silent_audio_inserted": silent_audio_inserted,
                "normalized_audio_format": f"{NORMALIZED_AUDIO_CODEC}/{NORMALIZED_AUDIO_SAMPLE_RATE}Hz/{NORMALIZED_AUDIO_CHANNELS}ch",
                "audio_sample_rate": NORMALIZED_AUDIO_SAMPLE_RATE,
                "audio_channels": NORMALIZED_AUDIO_CHANNELS,
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

        # Real functional check for exactly the symptom this fix pack
        # targets: a stream-layout mismatch made the old code's rendered
        # duration balloon (a 3-segment, 9s-expected clip came out as 12s,
        # because the mismatched silent track's audio never stopped). ffmpeg
        # prints a few harmless "Non-monotonic DTS" lines even for correctly
        # normalized segments (AAC's inherent few-millisecond encoder-delay
        # at independently-encoded segment boundaries) -- matching that exact
        # log text would fail every render, even fixed ones (confirmed while
        # building this fix). Measuring the *actual* rendered duration against
        # what was expected is the real, content-based proof instead.
        final_duration = _ffprobe_duration_seconds(final_path)
        expected_duration = sum(included_durations)
        if final_duration is not None and abs(final_duration - expected_duration) > 1.5:
            raise FfmpegError(
                "مدة الفيديو النهائي لا تطابق مجموع مدد المشاهد المتوقعة -- قد يكون مسار الصوت "
                "غير متطابق بين المشاهد. تم إيقاف التجميع بدل تسليم فيديو صوته غير سليم."
            )

        # Post-render safety net (Milestone B.4, strengthened 2026-06-28):
        # every segment always has an audio stream now (real or silent), so
        # the final file must have exactly one consistent audio stream too --
        # if it doesn't despite at least one scene having real saved audio,
        # treat that as a clear render failure instead of silently shipping a
        # video with no usable (or partially missing) audio.
        audio_info = _final_video_audio_stream_info(final_path)
        if any_scene_has_audio and audio_info is None:
            raise FfmpegError("الفيديو النهائي لا يحتوي على مسار صوت رغم وجود صوت محفوظ لبعض المشاهد.")
        if (
            any_scene_has_audio
            and audio_info is not None
            and (
                audio_info["sample_rate"] != NORMALIZED_AUDIO_SAMPLE_RATE
                or audio_info["channels"] != NORMALIZED_AUDIO_CHANNELS
            )
        ):
            raise FfmpegError(
                "مسار الصوت في الفيديو النهائي غير متطابق مع التنسيق الموحّد المتوقع -- "
                "تم إيقاف التجميع تجنباً لفيديو صوته غير سليم."
            )

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
