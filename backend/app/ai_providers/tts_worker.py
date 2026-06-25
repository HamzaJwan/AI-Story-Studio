from __future__ import annotations

import time
from typing import Any

import requests

from app.config import Settings


class TtsWorkerError(RuntimeError):
    pass


class TtsWorkerClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = settings.tts_enabled
        self.service_url = settings.tts_service_url.rstrip("/")
        self.timeout = settings.tts_timeout_seconds

    def is_configured(self) -> bool:
        return self.settings.tts_configured

    def health(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "enabled": self.enabled,
            "configured": self.is_configured(),
            "service_url_configured": bool(self.service_url),
            "remote_ok": None,
        }
        if not self.is_configured():
            return data

        started = time.perf_counter()
        try:
            response = requests.get(f"{self.service_url}/health", timeout=min(self.timeout, 10))
            response.raise_for_status()
            data["remote_ok"] = True
        except requests.RequestException:
            data["remote_ok"] = False
        data["latency_ms"] = int((time.perf_counter() - started) * 1000)
        return data

    def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured():
            raise TtsWorkerError("خدمة الصوت غير مفعّلة.")
        try:
            response = requests.post(
                f"{self.service_url}/api/tts/jobs",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TtsWorkerError("تعذر الاتصال بخدمة الصوت.") from exc
        return response.json()

    def get_job(self, job_id: str) -> dict[str, Any]:
        if not self.is_configured():
            raise TtsWorkerError("خدمة الصوت غير مفعّلة.")
        try:
            response = requests.get(
                f"{self.service_url}/api/tts/jobs/{job_id}",
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TtsWorkerError("تعذر الاتصال بخدمة الصوت.") from exc
        return response.json()

    def download_file(self, job_id: str, fmt: str) -> tuple[bytes, str]:
        if not self.is_configured():
            raise TtsWorkerError("خدمة الصوت غير مفعّلة.")
        try:
            response = requests.get(
                f"{self.service_url}/api/tts/jobs/{job_id}/download/{fmt}",
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TtsWorkerError("تعذر الاتصال بخدمة الصوت.") from exc
        content_type = response.headers.get("content-type", "application/octet-stream")
        return response.content, content_type
