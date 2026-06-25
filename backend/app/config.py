from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "AI Story Studio"
    app_phase: str = "0.1"
    ollama_base_url: str = ""
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout_seconds: int = 180
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    data_dir: str = "./data"
    max_story_chars: int = 25000
    tts_enabled: bool = False
    tts_service_url: str = ""
    tts_timeout_seconds: int = 30
    image_service_enabled: bool = False
    image_service_url: str = ""
    image_timeout_seconds: int = 120

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",")]
        return [origin for origin in origins if origin and origin != "*"]

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir)

    @property
    def ollama_configured(self) -> bool:
        value = self.ollama_base_url.strip()
        return bool(value) and "AI_SERVER_LAN_IP" not in value and "YOUR_" not in value

    @property
    def tts_configured(self) -> bool:
        value = self.tts_service_url.strip()
        return self.tts_enabled and bool(value) and "AI_SERVER_LAN_IP" not in value and "YOUR_" not in value

    @property
    def image_configured(self) -> bool:
        value = self.image_service_url.strip()
        return (
            self.image_service_enabled
            and bool(value)
            and "AI_SERVER_LAN_IP" not in value
            and "YOUR_" not in value
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
