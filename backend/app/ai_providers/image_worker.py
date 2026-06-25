from __future__ import annotations

import time
from typing import Any

import requests

from app.config import Settings

# Matches deploy/ai-server/comfyui-lab's bundled workflow_sdxl_txt2img.json shape.
# Node "9" (SaveImage) is hardcoded since every job submitted here uses this exact
# workflow graph, only varying text/seed/dimensions.
CHECKPOINT_NAME = "sd_xl_base_1.0.safetensors"
SAVE_IMAGE_NODE_ID = "9"
DEFAULT_NEGATIVE_PROMPT = "blurry, low quality, distorted, watermark, text"


class ImageWorkerError(RuntimeError):
    pass


class ImageWorkerClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = settings.image_service_enabled
        self.service_url = settings.image_service_url.rstrip("/")
        self.timeout = settings.image_timeout_seconds

    def is_configured(self) -> bool:
        return self.settings.image_configured

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
            response = requests.get(f"{self.service_url}/system_stats", timeout=min(self.timeout, 10))
            response.raise_for_status()
            data["remote_ok"] = True
        except requests.RequestException:
            data["remote_ok"] = False
        data["latency_ms"] = int((time.perf_counter() - started) * 1000)
        return data

    def _build_workflow(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        seed: int,
    ) -> dict[str, Any]:
        return {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": 20,
                    "cfg": 7.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CHECKPOINT_NAME}},
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1},
            },
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative_prompt, "clip": ["4", 1]}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "scene", "images": ["8", 0]}},
        }

    def create_job(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int,
        negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    ) -> str:
        if not self.is_configured():
            raise ImageWorkerError("خدمة الصور غير مفعّلة.")
        workflow = self._build_workflow(prompt, negative_prompt, width, height, seed)
        try:
            response = requests.post(
                f"{self.service_url}/prompt",
                json={"prompt": workflow},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise ImageWorkerError("تعذر الاتصال بخدمة الصور.") from exc

        if data.get("node_errors"):
            raise ImageWorkerError(f"تم رفض workflow توليد الصورة: {data['node_errors']}")
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise ImageWorkerError("لم ترجع خدمة الصور رقم مهمة (job id).")
        return prompt_id

    def get_job(self, job_id: str) -> dict[str, Any]:
        if not self.is_configured():
            raise ImageWorkerError("خدمة الصور غير مفعّلة.")
        try:
            response = requests.get(f"{self.service_url}/history/{job_id}", timeout=self.timeout)
            response.raise_for_status()
            history = response.json()
        except requests.RequestException as exc:
            raise ImageWorkerError("تعذر الاتصال بخدمة الصور.") from exc

        entry = history.get(job_id)
        if entry is None:
            return {"job_id": job_id, "status": "running", "error": None, "files": []}

        status = entry.get("status", {})
        if status.get("status_str") == "error":
            return {"job_id": job_id, "status": "failed", "error": "Image generation failed.", "files": []}
        if not status.get("completed"):
            return {"job_id": job_id, "status": "running", "error": None, "files": []}

        images = entry.get("outputs", {}).get(SAVE_IMAGE_NODE_ID, {}).get("images", [])
        files = [
            {
                "filename": img["filename"],
                "subfolder": img.get("subfolder", ""),
                "type": img.get("type", "output"),
            }
            for img in images
        ]
        return {"job_id": job_id, "status": "done", "error": None, "files": files}

    def download_file(self, filename: str, subfolder: str, file_type: str) -> tuple[bytes, str]:
        if not self.is_configured():
            raise ImageWorkerError("خدمة الصور غير مفعّلة.")
        try:
            response = requests.get(
                f"{self.service_url}/view",
                params={"filename": filename, "subfolder": subfolder, "type": file_type},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ImageWorkerError("تعذر الاتصال بخدمة الصور.") from exc
        content_type = response.headers.get("content-type", "image/png")
        return response.content, content_type
