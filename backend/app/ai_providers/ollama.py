from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

from app.config import Settings


class OllamaError(RuntimeError):
    pass


class OllamaTimeoutError(OllamaError):
    """Raised only for a real request timeout (Ollama reachable, but the
    request -- often a long-story chunk -- took longer than the configured
    timeout). Kept as a distinct, narrow subclass of `OllamaError` so callers
    can specifically catch *just* the timeout case (to trigger chunk-splitting
    recovery) while every existing `except OllamaError` site still catches it
    too, unchanged. Carries only `timeout_seconds` and a safe message -- never
    a URL, prompt, or story text."""

    def __init__(self, timeout_seconds: int, message: str):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


_CONTEXT_OVERFLOW_HINTS = ("context", "too long", "exceed", "out of memory", "token")


def _looks_like_context_overflow(body_snippet: str) -> bool:
    lowered = body_snippet.lower()
    return any(hint in lowered for hint in _CONTEXT_OVERFLOW_HINTS)


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
            raise OllamaError("خدمة Ollama غير مهيأة. تأكد من ضبط OLLAMA_BASE_URL في ملف .env المحلي.")

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
        except requests.exceptions.Timeout as exc:
            # Covers both connect-timeout and read-timeout. This is NOT a connection
            # failure -- Ollama is reachable but the request (often a long story sent
            # as one prompt) took longer than `self.timeout`. Misreporting this as a
            # "service unreachable" error was the manual-QA bug: a healthy Ollama with
            # a long story would still show a connection-refused-style message.
            #
            # This message is only ever shown to the user for the single-shot
            # (non-chunked) call path. When this is raised from inside the
            # long-story chunk loop, `StoryEngine` catches `OllamaTimeoutError`
            # specifically and replaces this message with a chunk-aware one
            # (see story_engine/engine.py) -- so a user who is already in long
            # story mode never sees "جرّب وضع تحسين القصص الطويلة" again.
            raise OllamaTimeoutError(
                timeout_seconds=self.timeout,
                message=(
                    f"استغرق الطلب وقتاً أطول من {self.timeout} ثانية (Timeout). "
                    "إذا كانت القصة طويلة، جرّب وضع تحسين القصص الطويلة أو قسّم النص إلى أجزاء أصغر."
                ),
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise OllamaError(
                "تعذر الاتصال بخدمة Ollama. تحقق من ملف .env المحلي ومن تشغيل الخادم."
            ) from exc
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            body_snippet = (exc.response.text or "") if exc.response is not None else ""
            if _looks_like_context_overflow(body_snippet):
                raise OllamaError(
                    "النص طويل جداً على الموديل الحالي (تجاوز سعة السياق). "
                    "جرّب وضع تحسين القصص الطويلة أو قسّم النص إلى أجزاء أصغر."
                ) from exc
            raise OllamaError(f"خدمة Ollama أعادت خطأ (HTTP {status_code}).") from exc
        except requests.RequestException as exc:
            raise OllamaError("تعذر الاتصال بخدمة Ollama. تحقق من ملف .env المحلي ومن تشغيل الخادم.") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        data = response.json()
        text = str(data.get("response", "")).strip()
        if not text:
            raise OllamaError("استجابة فارغة من خدمة Ollama.")
        return OllamaResult(text=text, latency_ms=latency_ms, model=selected_model)
