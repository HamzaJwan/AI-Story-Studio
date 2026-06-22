from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

from app.config import Settings


class OllamaError(RuntimeError):
    pass


@dataclass
class OllamaResult:
    text: str
    latency_ms: int
    model: str


class OllamaProvider:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout_seconds

    def is_configured(self) -> bool:
        return self.settings.ollama_configured

    def health(self) -> dict[str, Any]:
        if not self.is_configured():
            return {
                "ok": False,
                "provider": "ollama",
                "model": self.model,
                "base_url_configured": False,
                "latency_ms": None,
            }

        started = time.perf_counter()
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=min(self.timeout, 10))
            response.raise_for_status()
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {
                "ok": True,
                "provider": "ollama",
                "model": self.model,
                "base_url_configured": True,
                "latency_ms": latency_ms,
            }
        except requests.RequestException:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {
                "ok": False,
                "provider": "ollama",
                "model": self.model,
                "base_url_configured": True,
                "latency_ms": latency_ms,
            }

    def generate_text(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        num_ctx: int = 8192,
        num_predict: int | None = None,
    ) -> OllamaResult:
        if not self.is_configured():
            raise OllamaError("Ollama is not configured. Set OLLAMA_BASE_URL in local .env.")

        selected_model = model or self.model
        started = time.perf_counter()
        payload = {
            "model": selected_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
            },
        }
        if num_predict is not None:
            payload["options"]["num_predict"] = num_predict

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError("Ollama request failed. Check local .env and server availability.") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        data = response.json()
        text = str(data.get("response", "")).strip()
        if not text:
            raise OllamaError("Ollama returned an empty response.")
        return OllamaResult(text=text, latency_ms=latency_ms, model=selected_model)
