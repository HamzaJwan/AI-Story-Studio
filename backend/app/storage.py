from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import Settings
from app.schemas import (
    ProjectCreateRequest,
    ProjectListItem,
    ProjectResponse,
    ProjectUpdateRequest,
    SplitScenesData,
)


PROJECT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{8,80}$")


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

    def scenes_export(self, project_id: str) -> dict[str, object]:
        project = self.get_project(project_id)
        return {
            "project_id": project.project_id,
            "story_title": project.title,
            "scenes": [scene.model_dump() for scene in project.scenes],
        }

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
