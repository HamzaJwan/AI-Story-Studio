from typing import Any

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
