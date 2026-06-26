from __future__ import annotations

import io
import json
import re
import subprocess
import wave
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import Settings
from app.schemas import (
    ProjectCreateRequest,
    ProjectListItem,
    ProjectResponse,
    ProjectUpdateRequest,
    Scene,
    SplitScenesData,
)


PROJECT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{8,80}$")


def _concatenate_wavs(paths: list[Path]) -> bytes | None:
    """Concatenate same-format WAV files in order. No ffmpeg/MP3 dependency."""
    try:
        with wave.open(str(paths[0]), "rb") as first:
            params = first.getparams()
        frames: list[bytes] = []
        for path in paths:
            with wave.open(str(path), "rb") as wav_file:
                if wav_file.getparams()[:3] != params[:3]:
                    return None
                frames.append(wav_file.readframes(wav_file.getnframes()))
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as out:
            out.setparams(params)
            for chunk in frames:
                out.writeframes(chunk)
        return buffer.getvalue()
    except (OSError, wave.Error):
        return None


def get_audio_duration_seconds(path: Path) -> float | None:
    """Real duration of a saved scene audio file, in seconds.

    Tries the stdlib `wave` module first (every audio path in this app is
    WAV today -- generate-all and the frontend's single-scene job both
    always request format=wav). Falls back to `ffprobe` (already installed
    alongside ffmpeg for video assembly) for any other format, so this
    stays correct even if MP3 is ever used. Returns None if both fail.
    """
    try:
        with wave.open(str(path), "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            if rate > 0:
                return frames / float(rate)
    except (OSError, wave.Error):
        pass
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return None


def _format_srt_timestamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_vtt_timestamp(seconds: float) -> str:
    return _format_srt_timestamp(seconds).replace(",", ".")


def _subtitle_cues(scenes: list[Scene], durations: list[float]) -> list[tuple[float, float, str]]:
    """One cue per scene, timed cumulatively by the same per-scene durations
    used for video assembly (`ProjectStorage.get_scene_render_durations()`) --
    the real saved-audio duration when present, else `duration_seconds`.

    No word-level alignment (out of scope for the MVP) -- each scene's full
    narration_ar is shown for its whole duration.
    """
    cues: list[tuple[float, float, str]] = []
    start = 0.0
    for scene, duration in zip(scenes, durations):
        text = scene.narration_ar.strip()
        end = start + duration
        if text:
            cues.append((start, end, text))
        start = end
    return cues


def _build_srt(scenes: list[Scene], durations: list[float]) -> str:
    lines: list[str] = []
    for index, (start, end, text) in enumerate(_subtitle_cues(scenes, durations), start=1):
        lines.append(str(index))
        lines.append(f"{_format_srt_timestamp(start)} --> {_format_srt_timestamp(end)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _build_vtt(scenes: list[Scene], durations: list[float]) -> str:
    lines: list[str] = ["WEBVTT", ""]
    for index, (start, end, text) in enumerate(_subtitle_cues(scenes, durations), start=1):
        lines.append(str(index))
        lines.append(f"{_format_vtt_timestamp(start)} --> {_format_vtt_timestamp(end)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


class ProjectStorage:
    def __init__(self, settings: Settings):
        self.root = settings.data_path / "projects"
        self.root.mkdir(parents=True, exist_ok=True)

    def save_story_project(
        self,
        story_text: str,
        split_data: SplitScenesData,
        provider: str,
        model: str,
    ) -> SplitScenesData:
        project = self.create_project(
            ProjectCreateRequest(
                title=split_data.story_title,
                original_story=story_text,
                improved_story="",
                scenes=split_data.scenes,
            ),
            meta={"provider": provider, "model": model, "source": "split-scenes"},
        )
        split_data.project_id = project.project_id
        return split_data

    def create_project(
        self,
        request: ProjectCreateRequest,
        meta: dict[str, str] | None = None,
    ) -> ProjectResponse:
        now = datetime.now(timezone.utc)
        project = ProjectResponse(
            project_id=self._new_project_id(),
            title=request.title,
            original_story=request.original_story,
            improved_story=request.improved_story,
            scenes=request.scenes,
            created_at=now,
            updated_at=now,
            story_style_bible=request.story_style_bible,
            character_bible=request.character_bible,
            location_bible=request.location_bible,
            object_bible=request.object_bible,
            negative_prompt=request.negative_prompt,
            style_preset=request.style_preset,
            video_mode=request.video_mode,
            video_transition=request.video_transition,
            safety_source_type=request.safety_source_type,
            safety_consent_confirmed=request.safety_consent_confirmed,
            safety_rights_notes=request.safety_rights_notes,
            safety_applies_to=request.safety_applies_to,
        )
        self._write_project(project, meta=meta)
        return project

    def list_projects(self) -> list[ProjectListItem]:
        projects: list[ProjectListItem] = []
        for path in sorted(self.root.glob("*.json")):
            if path.name.endswith(".scenes.json"):
                continue
            try:
                project = self._read_project_file(path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            projects.append(
                ProjectListItem(
                    project_id=project.project_id,
                    title=project.title,
                    scene_count=len(project.scenes),
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                )
            )
        return sorted(projects, key=lambda item: item.updated_at, reverse=True)

    def get_project(self, project_id: str) -> ProjectResponse:
        return self._read_project_file(self._project_path(project_id))

    def update_project(
        self,
        project_id: str,
        request: ProjectUpdateRequest,
    ) -> ProjectResponse:
        project = self.get_project(project_id)
        update_data = request.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)
        project.updated_at = datetime.now(timezone.utc)
        self._write_project(project)
        return project

    def delete_project(self, project_id: str) -> None:
        path = self._project_path(project_id)
        if not path.exists():
            raise FileNotFoundError("Project not found.")
        path.unlink()

    def project_audio_dir(self, project_id: str) -> Path:
        safe_id = self._project_path(project_id).stem
        path = self.root / safe_id / "audio"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_scene_audio(
        self,
        project_id: str,
        scene_id: str,
        audio_bytes: bytes,
        fmt: str,
    ) -> ProjectResponse:
        project = self.get_project(project_id)
        scene = next((s for s in project.scenes if s.scene_id == scene_id), None)
        if scene is None:
            raise FileNotFoundError("Scene not found in project.")

        audio_dir = self.project_audio_dir(project_id)
        audio_path = audio_dir / f"scene_{scene_id}.{fmt}"
        audio_path.write_bytes(audio_bytes)

        scene.audio_generated_at = datetime.now(timezone.utc)
        scene.audio_bytes = len(audio_bytes)
        scene.audio_format = fmt
        project.updated_at = datetime.now(timezone.utc)
        self._write_project(project)
        return project

    def get_scenes_with_audio(self, project: ProjectResponse) -> list[Scene]:
        audio_dir = self.project_audio_dir(project.project_id)
        return [
            scene
            for scene in project.scenes
            if scene.audio_format
            and (audio_dir / f"scene_{scene.scene_id}.{scene.audio_format}").exists()
        ]

    def get_scene_audio_path(self, project_id: str, scene_id: str) -> Path | None:
        project = self.get_project(project_id)
        scene = next((s for s in project.scenes if s.scene_id == scene_id), None)
        if scene is None or not scene.audio_format:
            return None
        audio_dir = self.project_audio_dir(project_id)
        candidate = (audio_dir / f"scene_{scene.scene_id}.{scene.audio_format}").resolve()
        if audio_dir.resolve() not in candidate.parents:
            return None
        return candidate if candidate.exists() else None

    def project_images_dir(self, project_id: str) -> Path:
        safe_id = self._project_path(project_id).stem
        path = self.root / safe_id / "images"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_scene_image(
        self,
        project_id: str,
        scene_id: str,
        image_bytes: bytes,
        fmt: str,
        width: int,
        height: int,
        engine: str,
        seed: int,
        prompt_used: str,
    ) -> ProjectResponse:
        project = self.get_project(project_id)
        scene = next((s for s in project.scenes if s.scene_id == scene_id), None)
        if scene is None:
            raise FileNotFoundError("Scene not found in project.")

        images_dir = self.project_images_dir(project_id)
        image_path = images_dir / f"scene_{scene_id}.{fmt}"
        image_path.write_bytes(image_bytes)

        scene.image_generated_at = datetime.now(timezone.utc)
        scene.image_bytes = len(image_bytes)
        scene.image_format = fmt
        scene.image_width = width
        scene.image_height = height
        scene.image_engine = engine
        scene.image_seed = seed
        scene.image_prompt_used = prompt_used
        project.updated_at = datetime.now(timezone.utc)
        self._write_project(project)
        return project

    def get_scenes_with_images(self, project: ProjectResponse) -> list[Scene]:
        images_dir = self.project_images_dir(project.project_id)
        return [
            scene
            for scene in project.scenes
            if scene.image_format
            and (images_dir / f"scene_{scene.scene_id}.{scene.image_format}").exists()
        ]

    def get_scene_image_path(self, project_id: str, scene_id: str) -> Path | None:
        project = self.get_project(project_id)
        scene = next((s for s in project.scenes if s.scene_id == scene_id), None)
        if scene is None or not scene.image_format:
            return None
        images_dir = self.project_images_dir(project_id)
        candidate = (images_dir / f"scene_{scene.scene_id}.{scene.image_format}").resolve()
        if images_dir.resolve() not in candidate.parents:
            return None
        return candidate if candidate.exists() else None

    def project_video_dir(self, project_id: str) -> Path:
        safe_id = self._project_path(project_id).stem
        path = self.root / safe_id / "video"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_video_path(self, project_id: str) -> Path | None:
        video_dir = self.project_video_dir(project_id)
        candidate = (video_dir / "final_story.mp4").resolve()
        if video_dir.resolve() not in candidate.parents:
            return None
        return candidate if candidate.exists() else None

    def get_video_metadata(self, project_id: str) -> dict | None:
        video_dir = self.project_video_dir(project_id)
        meta_path = video_dir / "metadata.json"
        if not meta_path.exists():
            return None
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def save_video_metadata(self, project_id: str, metadata: dict) -> None:
        video_dir = self.project_video_dir(project_id)
        (video_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def build_final_story_wav(self, project_id: str) -> bytes | None:
        project = self.get_project(project_id)
        audio_dir = self.project_audio_dir(project_id)
        wav_paths = [
            audio_dir / f"scene_{scene.scene_id}.wav"
            for scene in self.get_scenes_with_audio(project)
            if scene.audio_format == "wav"
        ]
        if len(wav_paths) < 2:
            return None
        return _concatenate_wavs(wav_paths)

    def get_scene_render_durations(self, project: ProjectResponse) -> list[float]:
        """Per-scene duration in seconds: the real saved-audio duration when
        a scene has one, else the stored `duration_seconds` estimate.

        This is the single source of truth shared by video assembly
        (`videos.py`) and subtitle timing (`build_srt`/`build_vtt`/
        `build_export_zip`) so a rendered video and its sidecar subtitles
        can never drift out of sync with each other.
        """
        audio_dir = self.project_audio_dir(project.project_id)
        durations: list[float] = []
        for scene in project.scenes:
            duration = float(scene.duration_seconds)
            if scene.audio_format:
                audio_path = audio_dir / f"scene_{scene.scene_id}.{scene.audio_format}"
                if audio_path.exists():
                    real_duration = get_audio_duration_seconds(audio_path)
                    if real_duration and real_duration > 0:
                        duration = real_duration
            durations.append(duration)
        return durations

    def build_srt(self, project_id: str) -> str:
        project = self.get_project(project_id)
        return _build_srt(project.scenes, self.get_scene_render_durations(project))

    def build_vtt(self, project_id: str) -> str:
        project = self.get_project(project_id)
        return _build_vtt(project.scenes, self.get_scene_render_durations(project))

    def scenes_export(self, project_id: str) -> dict[str, object]:
        project = self.get_project(project_id)
        return {
            "project_id": project.project_id,
            "story_title": project.title,
            "scenes": [scene.model_dump(mode="json") for scene in project.scenes],
        }

    def build_export_zip(self, project_id: str) -> bytes:
        project = self.get_project(project_id)
        scenes_payload = self.scenes_export(project_id)
        scene_durations = self.get_scene_render_durations(project)
        total_duration = round(sum(scene_durations))
        audio_dir = self.project_audio_dir(project_id)
        scenes_with_audio = self.get_scenes_with_audio(project)
        images_dir = self.project_images_dir(project_id)
        scenes_with_images = self.get_scenes_with_images(project)
        video_path = self.get_video_path(project_id)
        metadata = {
            "project_id": project.project_id,
            "title": project.title,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
            "scene_count": len(project.scenes),
            "total_duration_seconds": total_duration,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "app": "AI Story Studio",
            "phase": "3.1",
            "audio_scene_count": len(scenes_with_audio),
            "audio_limitations": [
                "final_story.wav is a raw WAV concatenation of available scene audio in scene order, "
                "built with Python's wave module rather than ffmpeg; convert externally if MP3 is needed.",
            ]
            if scenes_with_audio
            else [],
            "image_scene_count": len(scenes_with_images),
            "image_limitations": [
                "Image quality is CANDIDATE, not final-approved (see "
                "docs/IMAGE_QUALITY_APPROVAL_CHECKLIST.md). Continuity is prompt-only (Tier 1) -- "
                "consistent style/character/location text, not pixel-level guarantees.",
            ]
            if scenes_with_images
            else [],
            "video_included": video_path is not None,
            "video_limitations": [
                "Basic ffmpeg assembly (static scene images + scene audio), no AI video motion, "
                "transitions, or burned-in subtitles -- see docs/VIDEO_SUBTITLES_PLAN.md.",
            ]
            if video_path is not None
            else [],
        }

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("story.txt", project.original_story)
            archive.writestr("improved_story.txt", project.improved_story)
            archive.writestr(
                "scenes.json",
                json.dumps(scenes_payload, ensure_ascii=False, indent=2),
            )
            archive.writestr(
                "metadata.json",
                json.dumps(metadata, ensure_ascii=False, indent=2),
            )
            archive.writestr("subtitles/story.srt", _build_srt(project.scenes, scene_durations))
            archive.writestr("subtitles/story.vtt", _build_vtt(project.scenes, scene_durations))
            for scene in scenes_with_audio:
                audio_path = audio_dir / f"scene_{scene.scene_id}.{scene.audio_format}"
                archive.writestr(f"audio/scene_{scene.scene_id}.{scene.audio_format}", audio_path.read_bytes())
            wav_paths = [
                audio_dir / f"scene_{scene.scene_id}.wav"
                for scene in scenes_with_audio
                if scene.audio_format == "wav"
            ]
            if len(wav_paths) > 1:
                final_wav = _concatenate_wavs(wav_paths)
                if final_wav is not None:
                    archive.writestr("audio/final_story.wav", final_wav)
            for scene in scenes_with_images:
                image_path = images_dir / f"scene_{scene.scene_id}.{scene.image_format}"
                archive.writestr(f"images/scene_{scene.scene_id}.{scene.image_format}", image_path.read_bytes())
            if video_path is not None:
                archive.writestr("video/final_story.mp4", video_path.read_bytes())
        return buffer.getvalue()

    def _new_project_id(self) -> str:
        return str(uuid4())

    def _project_path(self, project_id: str) -> Path:
        safe_id = project_id.strip()
        if not PROJECT_ID_PATTERN.fullmatch(safe_id):
            raise FileNotFoundError("Invalid project id.")
        path = (self.root / f"{safe_id}.json").resolve()
        if self.root.resolve() not in path.parents:
            raise FileNotFoundError("Invalid project path.")
        return path

    def _read_project_file(self, path: Path) -> ProjectResponse:
        if not path.exists():
            raise FileNotFoundError("Project not found.")
        return ProjectResponse.model_validate_json(path.read_text(encoding="utf-8"))

    def _write_project(
        self,
        project: ProjectResponse,
        meta: dict[str, str] | None = None,
    ) -> None:
        payload = project.model_dump(mode="json")
        if meta:
            payload["meta"] = meta
        self._project_path(project.project_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
