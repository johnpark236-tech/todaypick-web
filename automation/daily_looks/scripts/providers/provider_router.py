"""Priority-based provider router for TodayPick single-first autonomous generation."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from .base_provider import SingleImageProvider
from .openart_provider import OpenArtProvider
from .fal_provider import FalProvider
from .picsart_provider import PicsartProvider

logger = logging.getLogger(__name__)

_CONFIG_ROOT = Path(__file__).resolve().parents[2] / "config"
_DEFAULT_PRIORITY = ["openart", "fal", "picsart"]
_PROVIDER_CLASSES = {
    "openart": OpenArtProvider,
    "fal": FalProvider,
    "picsart": PicsartProvider,
}


def _resolve_priority() -> List[str]:
    env_val = os.environ.get("TODAYPICK_PROVIDER_PRIORITY", "").strip()
    if env_val:
        return [p.strip() for p in env_val.split(",") if p.strip()]
    cfg = _CONFIG_ROOT / "provider_priority.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            return list(data.get("priority", _DEFAULT_PRIORITY))
        except Exception:
            pass
    return list(_DEFAULT_PRIORITY)


class ProviderRouter:
    """Try providers in priority order; fall through on failure."""

    def __init__(self, priority: Optional[List[str]] = None) -> None:
        self._priority = priority if priority is not None else _resolve_priority()
        self._providers: List[SingleImageProvider] = []
        for pid in self._priority:
            cls = _PROVIDER_CLASSES.get(pid)
            if cls is None:
                logger.warning("unknown provider id in priority list: %s", pid)
                continue
            p = cls()
            if p.is_available():
                self._providers.append(p)
                logger.info("provider ready: %s", pid)
            else:
                logger.debug("provider %s skipped (key not set)", pid)

        if not self._providers:
            raise RuntimeError(
                "no single-first image provider is available; "
                "set at least one of: OPENART_API_KEY, FAL_KEY, PICSART_API_KEY"
            )

    @property
    def available_providers(self) -> List[str]:
        return [p.provider_id for p in self._providers]

    def generate_single(
        self,
        prompt: str,
        negative_prompt: str,
        output_path: Path,
        width: int = 648,
        height: int = 1152,
    ) -> dict:
        """Generate one single-cut portrait image. Tries each provider in order."""
        errors: List[str] = []
        for provider in self._providers:
            try:
                result = provider.generate_single(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    output_path=output_path,
                    width=width,
                    height=height,
                )
                logger.info("generated %s via %s", output_path.name, provider.provider_id)
                return result
            except Exception as exc:
                logger.warning("provider %s failed: %s", provider.provider_id, exc)
                errors.append(f"{provider.provider_id}: {exc}")

        raise RuntimeError(
            f"all providers failed for {output_path.name}: " + "; ".join(errors)
        )
