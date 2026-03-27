from __future__ import annotations

import base64
import logging
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from .automation import WindowsAutomation
from .config import AppSettings
from .models import ActionResult


class ImageGenerationService:
    def __init__(self, settings: AppSettings, automation: WindowsAutomation) -> None:
        self.settings = settings
        self.automation = automation
        self.logger = logging.getLogger(__name__)

    def generate(self, prompt: str) -> ActionResult:
        if not self.settings.openai_api_key or not OpenAI:
            return ActionResult(False, "Image generation ke liye OPENAI_API_KEY aur openai package configure karna hoga.", "image_generation", "generate_image")
        try:
            kwargs = {"api_key": self.settings.openai_api_key}
            if self.settings.openai_base_url:
                kwargs["base_url"] = self.settings.openai_base_url
            client = OpenAI(**kwargs)
            response = client.images.generate(model=self.settings.image_model, prompt=prompt, size="1024x1024")
            image_bytes = base64.b64decode(response.data[0].b64_json)
            filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            saved_path = self.automation.save_generated_image(image_bytes, filename)
            return ActionResult(True, f"Image generate karke save kar diya: {saved_path}", "image_generation", "generate_image", steps=["Submitted prompt to image model.", "Saved generated image locally."], target=saved_path, payload={"path": saved_path, "prompt": prompt})
        except Exception as exc:  # pragma: no cover
            self.logger.exception("Image generation failed")
            return ActionResult(False, "Image generation fail ho gaya.", "image_generation", "generate_image", error=str(exc))
