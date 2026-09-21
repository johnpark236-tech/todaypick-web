"""Abstract base for single-first image generation providers."""

from __future__ import annotations

import io
from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image


def fit_and_save(raw_bytes: bytes, output_path: Path, width: int, height: int) -> None:
    """Resize raw image bytes to (width, height) with contain-fit and save as WebP.

    SAFE_FIT_MODE=contain per MASTER v3.2: blurred background fill is handled
    by callers when needed; here we just letterbox with neutral fill.
    """
    with Image.open(io.BytesIO(raw_bytes)) as img:
        img = img.convert("RGB")
        if img.size == (width, height):
            out = img.copy()
        else:
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (width, height), (245, 243, 240))
            x = (width - img.width) // 2
            y = (height - img.height) // 2
            canvas.paste(img, (x, y))
            out = canvas
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(str(output_path), "WEBP", quality=92)


class SingleImageProvider(ABC):
    """Base class for all single-first portrait image providers."""

    provider_id: str = "unknown"

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the required API key env var is set."""

    @abstractmethod
    def generate_single(
        self,
        prompt: str,
        negative_prompt: str,
        output_path: Path,
        width: int = 648,
        height: int = 1152,
    ) -> dict:
        """Generate one portrait image and save it to output_path as WebP.

        Returns: {"provider_id": str, "output_path": str, "width": int, "height": int}
        Raises RuntimeError on any failure (router will try next provider).
        """
