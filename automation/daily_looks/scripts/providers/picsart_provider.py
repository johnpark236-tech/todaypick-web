"""Picsart text-to-image provider for TodayPick single-first pipeline."""

from __future__ import annotations

import os
from pathlib import Path

from .base_provider import SingleImageProvider, fit_and_save

_BASE = os.environ.get("PICSART_API_BASE", "https://genai-api.picsart.io").rstrip("/")


class PicsartProvider(SingleImageProvider):
    provider_id = "picsart"

    def __init__(self) -> None:
        self._api_key = os.environ.get("PICSART_API_KEY", "").strip()

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
            raise RuntimeError("PICSART_API_KEY not set")

        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("httpx is required for PicsartProvider: pip install httpx") from e

        headers = {
            "API-Key": self._api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "count": 1,
            "format": "PNG",
        }

        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{_BASE}/v1/text2image", json=payload, headers=headers)
            resp.raise_for_status()
            body = resp.json()

            image_url = _extract_image_url(body)
            img_resp = client.get(image_url, timeout=60)
            img_resp.raise_for_status()

        fit_and_save(img_resp.content, output_path, width, height)
        return {
            "provider_id": self.provider_id,
            "output_path": str(output_path),
            "width": width,
            "height": height,
        }


def _extract_image_url(body: object) -> str:
    if isinstance(body, list) and body:
        item = body[0]
        return str(item.get("url") or item.get("image_url") or "")
    if isinstance(body, dict):
        for key in ("url", "image_url"):
            if body.get(key):
                return str(body[key])
        for key in ("data", "images", "output"):
            items = body.get(key)
            if isinstance(items, list) and items:
                item = items[0]
                return str(item.get("url") or item.get("image_url") or "")
    raise RuntimeError(f"could not extract image URL from Picsart response: {body!r}")
