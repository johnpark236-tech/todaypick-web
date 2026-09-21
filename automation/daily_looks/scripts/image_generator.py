import os
import json
from pathlib import Path
from PIL import Image, ImageDraw

class ImageGeneratorAdapter:
    """Abstract interface for image generation backend"""
    def generate(self, prompt, negative_prompt, output_path, aspect_ratio="16:9"):
        raise NotImplementedError

class DryRunImageAdapter(ImageGeneratorAdapter):
    """Dry-run adapter that validates parameters without consuming API quota"""
    def __init__(self):
        self.backend_name = "DRY_RUN"

    def generate(self, prompt, negative_prompt, output_path, aspect_ratio="16:9"):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Create lightweight placeholder for dry run verification
        im = Image.new("RGB", (1376, 768), "#F5F3FF")
        d = ImageDraw.Draw(im)
        d.text((40, 40), f"[DRY_RUN] Image Generation Simulated\nPrompt Length: {len(prompt)}", fill=(108, 85, 232))
        im.save(output_path, "JPEG", quality=85)
        return True, "Dry-run success"

class GeminiImageAdapter(ImageGeneratorAdapter):
    """Adapter for official Google Gemini / Imagen API"""
    def __init__(self):
        self.backend_name = "GEMINI_API"
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    def is_available(self):
        return bool(self.api_key)

    def generate(self, prompt, negative_prompt, output_path, aspect_ratio="16:9"):
        if not self.is_available():
            return False, "API key not found in GEMINI_API_KEY or GOOGLE_API_KEY environment variables."
        # Call official Google generative AI image API if configured
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            result = client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=prompt,
                config=dict(number_of_images=1, aspect_ratio=aspect_ratio)
            )
            for generated_image in result.generated_images:
                image = Image.open(io.BytesIO(generated_image.image.image_bytes))
                image.save(output_path)
            return True, "Image generated via Gemini Imagen API"
        except Exception as e:
            return False, f"Gemini API generation error: {str(e)}"

class MultiProviderImageAdapter(ImageGeneratorAdapter):
    """Adapter that delegates to the ProviderRouter (OpenArt / fal / Picsart)."""

    def __init__(self):
        self.backend_name = "MULTI_PROVIDER"
        self._router = None

    def _get_router(self):
        if self._router is None:
            from providers.provider_router import ProviderRouter
            self._router = ProviderRouter()
        return self._router

    def is_available(self):
        try:
            router = self._get_router()
            return bool(router.available_providers)
        except Exception:
            return False

    def generate(self, prompt, negative_prompt, output_path, aspect_ratio="9:16"):
        output_path = Path(output_path)
        # Resolve width/height from aspect_ratio; default to single-cut spec 648x1152.
        if aspect_ratio in ("9:16", "portrait"):
            width, height = 648, 1152
        elif aspect_ratio in ("16:9", "landscape"):
            width, height = 1152, 648
        elif aspect_ratio == "1:1":
            width, height = 1024, 1024
        else:
            width, height = 648, 1152
        try:
            self._get_router().generate_single(
                prompt=prompt,
                negative_prompt=negative_prompt,
                output_path=output_path,
                width=width,
                height=height,
            )
            return True, f"generated via {self.backend_name}"
        except Exception as exc:
            return False, str(exc)


def get_image_generator(dry_run=True):
    if dry_run:
        return DryRunImageAdapter()
    multi = MultiProviderImageAdapter()
    if multi.is_available():
        return multi
    gemini = GeminiImageAdapter()
    if gemini.is_available():
        return gemini
    return DryRunImageAdapter()
