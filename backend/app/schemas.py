from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ApiEnvelope(BaseModel):
    data: Any
    meta: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class OllamaTestRequest(BaseModel):
    model: str | None = None


class ImproveStoryRequest(BaseModel):
    story_text: str = Field(min_length=1)
    tone: str = "عسكري هادئ"
    language: str = "ar"

    @field_validator("story_text")
    @classmethod
    def strip_story(cls, value: str) -> str:
        return value.strip()


class SplitScenesRequest(BaseModel):
    title: str = "قصة جديدة"
    story_text: str = Field(min_length=1)
    target_scenes: int = Field(default=6, ge=1, le=12)
    tone: str = "عسكري هادئ"

    @field_validator("title", "story_text", "tone")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class Scene(BaseModel):
    scene_id: str
    title_ar: str
    narration_ar: str
    visual_description_ar: str
    image_prompt_en: str
    duration_seconds: int = Field(ge=3, le=180)


class SplitScenesData(BaseModel):
    project_id: str | None = None
    story_title: str
    scenes: list[Scene] = Field(min_length=1)


class ProjectCreateRequest(BaseModel):
    title: str = Field(default="قصة جديدة", min_length=1, max_length=180)
    original_story: str = Field(default="", max_length=25000)
    improved_story: str = Field(default="", max_length=30000)
    scenes: list[Scene] = Field(default_factory=list)

    @field_validator("title", "original_story", "improved_story")
    @classmethod
    def strip_project_text(cls, value: str) -> str:
        return value.strip()


class ProjectUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    original_story: str | None = Field(default=None, max_length=25000)
    improved_story: str | None = Field(default=None, max_length=30000)
    scenes: list[Scene] | None = None

    @field_validator("title", "original_story", "improved_story")
    @classmethod
    def strip_optional_project_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value


class ProjectResponse(BaseModel):
    project_id: str
    title: str
    original_story: str = ""
    improved_story: str = ""
    scenes: list[Scene] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ProjectListItem(BaseModel):
    project_id: str
    title: str
    scene_count: int = 0
    created_at: datetime
    updated_at: datetime


class TtsJobRequest(BaseModel):
    mode: Literal["scene", "project"] = "project"
    scene_id: str | None = None
    voice_id: str | None = None
    speed: float | None = None
    format: Literal["wav", "mp3"] = "wav"
