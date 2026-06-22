from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import Settings
from app.schemas import SplitScenesData


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
        project_id = str(uuid4())
        project_dir = self.root / project_id
        project_dir.mkdir(parents=True, exist_ok=False)

        split_data.project_id = project_id
        (project_dir / "story.txt").write_text(story_text, encoding="utf-8")
        (project_dir / "scenes.json").write_text(
            json.dumps(split_data.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        metadata = {
            "project_id": project_id,
            "story_title": split_data.story_title,
            "provider": provider,
            "model": model,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "phase": "0.1",
        }
        (project_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return split_data

    def scenes_file_path(self, project_id: str) -> Path:
        safe_id = project_id.strip()
        if not safe_id or any(part in safe_id for part in ("..", "/", "\\")):
            raise FileNotFoundError("Invalid project id.")
        path = self.root / safe_id / "scenes.json"
        if not path.exists():
            raise FileNotFoundError("scenes.json not found.")
        return path
