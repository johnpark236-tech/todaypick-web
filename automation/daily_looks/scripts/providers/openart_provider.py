"""OpenArt text-to-image provider for TodayPick single-first pipeline."""

from __future__ import annotations

import os
import time
from pathlib import Path

from .base_provider import SingleImageProvider, fit_and_save

# Override via OPENART_API_BASE env var if endpoint changes.
_BASE = os.environ.get("OPENART_API_BASE", "https://openart.ai").rstrip("/")
# Polling: up to 60 attempts * 5s = 5 minutes max.
_POLL_INTERVAL = int(os.environ.get("OPENART_POLL_INTERVAL_SEC", "5"))
_POLL_MAX = int(os.environ.get("OPENART_POLL_MAX_ATTEMPTS", "60"))


class OpenArtProvider(SingleImageProvider):
    provider_id = "openart"

    def __init__(self) -> None:
        self._api_key = os.environ.get("OPENART_API_KEY", "").strip()
        self._model = os.environ.get("OPENART_MODEL_ID", "")

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate_single(
        self,
        prompt: str,
        negative_prompt: str,
        output_path: Path,
        width: int = 648,
        height: int = 1152,
    ) -> dict:
        if not self._api_key:
            raise RuntimeError("OPENART_API_KEY not set")

        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("httpx is required for OpenArtProvider: pip install httpx") from e

        headers = {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
        }
        payload: dict = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "num_images": 1,
            "width": width,
            "height": height,
            "output_format": "png",
        }
        if self._model:
            payload["model"] = self._model

        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{_BASE}/api/v2/create", json=payload, headers=headers)
            resp.raise_for_status()
            body = resp.json()

            # Some endpoints return images directly; others return a task_id.
            if "images" in body and body["images"]:
                image_url = body["images"][0].get("url") or body["images"][0].get("image_url")
            elif "task_id" in body:
                task_id = body["task_id"]
                image_url = self._poll_task(client, headers, task_id)
            else:
                raise RuntimeError(f"unexpected OpenArt response keys: {list(body.keys())}")

            img_resp = client.get(image_url, timeout=60)
            img_resp.raise_for_status()

        fit_and_save(img_resp.content, output_path, width, height)
        return {
            "provider_id": self.provider_id,
            "output_path": str(output_path),
            "width": width,
            "height": height,
        }

    def _poll_task(self, client, headers: dict, task_id: str) -> str:
        for _ in range(_POLL_MAX):
            time.sleep(_POLL_INTERVAL)
            poll = client.get(f"{_BASE}/api/v2/task/{task_id}", headers=headers)
            poll.raise_for_status()
            data = poll.json()
            status = str(data.get("status", "")).lower()
            if status in {"completed", "done", "success"}:
                images = data.get("images") or data.get("output_images") or []
                if not images:
                    raise RuntimeError(f"OpenArt task {task_id} completed but no images in response")
                return images[0].get("url") or images[0].get("image_url")
            if status in {"failed", "error", "cancelled"}:
                raise RuntimeError(f"OpenArt task {task_id} failed: {data.get('error') or status}")
        raise RuntimeError(f"OpenArt task {task_id} timed out after {_POLL_MAX * _POLL_INTERVAL}s")
