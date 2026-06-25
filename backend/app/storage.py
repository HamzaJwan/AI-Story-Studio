from __future__ import annotations

import io
import json
import re
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
        total_duration = sum(scene.duration_seconds for scene in project.scenes)
        audio_dir = self.project_audio_dir(project_id)
        scenes_with_audio = self.get_scenes_with_audio(project)
        images_dir = self.project_images_dir(project_id)
        scenes_with_images = self.get_scenes_with_images(project)
        metadata = {
            "project_id": project.project_id,
            "title": project.title,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
            "scene_count": len(project.scenes),
            "total_duration_seconds": total_duration,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "app": "AI Story Studio",
            "phase": "2.2",
            "audio_scene_count": len(scenes_with_audio),
            "audio_limitations": [
                "final_story.wav is a raw WAV concatenation of available scene audio in scene order "
                "(no ffmpeg/MP3 in the backend image); convert externally if MP3 is needed.",
            ]
            if scenes_with_audio
            else [],
            "image_scene_count": len(scenes_with_images),
            "image_limitations": [
                "Image quality is CANDIDATE, not final-approved (see "
                "docs/IMAGE_QUALITY_APPROVAL_CHECKLIST.md). No cross-scene continuity beyond "
                "prompt text -- character/location consistency is not guaranteed.",
            ]
            if scenes_with_images
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
