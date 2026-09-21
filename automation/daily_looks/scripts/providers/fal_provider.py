"""fal.ai text-to-image provider for TodayPick single-first pipeline."""

from __future__ import annotations

import os
import time
from pathlib import Path

from .base_provider import SingleImageProvider, fit_and_save

# Default model. Override via FAL_MODEL_ID env var.
# flux/schnell is fast and free-tier friendly; flux/dev gives better quality.
_DEFAULT_MODEL = "fal-ai/flux/schnell"
_BASE = "https://queue.fal.run"
_POLL_INTERVAL = int(os.environ.get("FAL_POLL_INTERVAL_SEC", "3"))
_POLL_MAX = int(os.environ.get("FAL_POLL_MAX_ATTEMPTS", "80"))


class FalProvider(SingleImageProvider):
    provider_id = "fal"

    def __init__(self) -> None:
        self._api_key = os.environ.get("FAL_KEY", "").strip()
        self._model_id = os.environ.get("FAL_MODEL_ID", _DEFAULT_MODEL).strip()

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
            raise RuntimeError("FAL_KEY not set")

        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("httpx is required for FalProvider: pip install httpx") from e

        headers = {
            "Authorization": f"Key {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "prompt": prompt,
            "image_size": {"width": width, "height": height},
            "num_images": 1,
            "output_format": "jpeg",
            "sync_mode": False,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        with httpx.Client(timeout=60) as client:
            resp = client.post(f"{_BASE}/{self._model_id}", json=payload, headers=headers)
            resp.raise_for_status()
            body = resp.json()

            if "images" in body and body["images"]:
                image_url = body["images"][0]["url"]
            elif "request_id" in body:
                image_url = self._poll_request(client, headers, body["request_id"])
            else:
                raise RuntimeError(f"unexpected fal response keys: {list(body.keys())}")

            img_resp = client.get(image_url, timeout=60)
            img_resp.raise_for_status()

        fit_and_save(img_resp.content, output_path, width, height)
        return {
            "provider_id": self.provider_id,
            "output_path": str(output_path),
            "width": width,
            "height": height,
            "model": self._model_id,
        }

    def _poll_request(self, client, headers: dict, request_id: str) -> str:
        status_url = f"{_BASE}/{self._model_id}/requests/{request_id}/status"
        result_url = f"{_BASE}/{self._model_id}/requests/{request_id}"
        for _ in range(_POLL_MAX):
            time.sleep(_POLL_INTERVAL)
            st = client.get(status_url, headers=headers)
            st.raise_for_status()
            st_data = st.json()
            status = str(st_data.get("status", "")).upper()
            if status == "COMPLETED":
                res = client.get(result_url, headers=headers)
                res.raise_for_status()
                images = res.json().get("images", [])
                if not images:
                    raise RuntimeError(f"fal request {request_id} completed but no images")
                return images[0]["url"]
            if status in {"FAILED", "CANCELLED"}:
                raise RuntimeError(
                    f"fal request {request_id} {status}: {st_data.get('error') or ''}"
                )
        raise RuntimeError(
            f"fal request {request_id} timed out after {_POLL_MAX * _POLL_INTERVAL}s"
        )
