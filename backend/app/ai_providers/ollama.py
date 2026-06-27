from __future__ import annotations

import json
import time
from collections.abc import Callable
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


class OllamaCancelledError(OllamaError):
    """Raised by `generate_text_streaming()` when `should_cancel()` returns
    True between stream events. A cooperative cancel, not a transport error --
    the in-flight HTTP response is closed deliberately."""


_CONTEXT_OVERFLOW_HINTS = ("context", "too long", "exceed", "out of memory", "token")


def _looks_like_context_overflow(body_snippet: str) -> bool:
    lowered = body_snippet.lower()
    return any(hint in lowered for hint in _CONTEXT_OVERFLOW_HINTS)


@dataclass
class OllamaResult:
    text: str
    latency_ms: int
    model: str
    # Populated from Ollama's own response (both streaming and non-streaming
    # responses include these in the final/only JSON object) -- used by the
    # story engine to detect silent truncation (Milestone 3) without ever
    # needing to inspect the actual text content.
    done_reason: str | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    prompt_eval_duration: int | None = None
    eval_duration: int | None = None


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
        return OllamaResult(
            text=text,
            latency_ms=latency_ms,
            model=selected_model,
            done_reason=data.get("done_reason"),
            prompt_eval_count=data.get("prompt_eval_count"),
            eval_count=data.get("eval_count"),
            prompt_eval_duration=data.get("prompt_eval_duration"),
            eval_duration=data.get("eval_duration"),
        )

    def generate_text_streaming(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        num_ctx: int = 8192,
        num_predict: int | None = None,
        connect_timeout_seconds: int = 10,
        read_timeout_seconds: int | None = None,
        on_stream_activity: Callable[[int, float], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> OllamaResult:
        """Streaming variant of `generate_text()` -- used only by job-based
        story improve (Milestone 2). Reads NDJSON line-by-line instead of
        waiting for the whole response, so the caller gets live activity
        (`on_stream_activity`) and can cooperatively cancel between events
        (`should_cancel`) instead of being blocked for the entire generation.

        Timeout model: `connect_timeout_seconds` bounds only the initial TCP
        connect. `read_timeout_seconds` (defaults to `self.timeout`) bounds
        the gap between consecutive stream events, not the total request
        duration -- as long as tokens keep arriving, the request is alive and
        is never considered stuck, no matter how long the whole generation
        takes. A real gap longer than `read_timeout_seconds` raises
        `OllamaTimeoutError`, same as the non-streaming path.

        Never logs prompt, story text, or any individual response fragment.
        """
        if not self.is_configured():
            raise OllamaError("خدمة Ollama غير مهيأة. تأكد من ضبط OLLAMA_BASE_URL في ملف .env المحلي.")

        read_timeout = read_timeout_seconds or self.timeout
        selected_model = model or self.model
        started = time.perf_counter()
        payload = {
            "model": selected_model,
            "prompt": prompt,
            "stream": True,
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
                timeout=(connect_timeout_seconds, read_timeout),
                stream=True,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as exc:
            raise OllamaTimeoutError(
                timeout_seconds=read_timeout,
                message=(
                    f"استغرق الطلب وقتاً أطول من {read_timeout} ثانية (Timeout) قبل بدء الاستجابة. "
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

        fragments: list[str] = []
        generated_units = 0
        done_reason: str | None = None
        prompt_eval_count: int | None = None
        eval_count: int | None = None
        prompt_eval_duration: int | None = None
        eval_duration: int | None = None
        try:
            for line in response.iter_lines(decode_unicode=True):
                if should_cancel and should_cancel():
                    raise OllamaCancelledError("تم إلغاء تحسين القصة.")
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    # Never log the raw line -- it may contain story text.
                    continue
                fragment = event.get("response", "")
                if fragment:
                    fragments.append(fragment)
                    generated_units += 1
                    if on_stream_activity:
                        on_stream_activity(generated_units, time.perf_counter() - started)
                if event.get("done"):
                    done_reason = event.get("done_reason")
                    prompt_eval_count = event.get("prompt_eval_count")
                    eval_count = event.get("eval_count")
                    prompt_eval_duration = event.get("prompt_eval_duration")
                    eval_duration = event.get("eval_duration")
                    break
        except OllamaCancelledError:
            raise
        except requests.exceptions.RequestException as exc:
            # The initial POST already succeeded -- a failure while iterating
            # the stream (including a stalled read longer than read_timeout)
            # means Ollama stopped responding mid-generation, not that it was
            # unreachable. Surface it the same way as the non-streaming
            # timeout so the existing chunk-split recovery can react to it.
            raise OllamaTimeoutError(
                timeout_seconds=read_timeout,
                message=(
                    f"توقف Ollama عن إرسال بيانات لأكثر من {read_timeout} ثانية أثناء التوليد. "
                    "قد يكون يعمل على CPU بسبب ضغط GPU."
                ),
            ) from exc
        finally:
            response.close()

        latency_ms = int((time.perf_counter() - started) * 1000)
        text = "".join(fragments).strip()
        if not text:
            raise OllamaError("استجابة فارغة من خدمة Ollama.")
        return OllamaResult(
            text=text,
            latency_ms=latency_ms,
            model=selected_model,
            done_reason=done_reason,
            prompt_eval_count=prompt_eval_count,
            eval_count=eval_count,
            prompt_eval_duration=prompt_eval_duration,
            eval_duration=eval_duration,
        )
