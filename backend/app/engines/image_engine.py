from abc import ABC, abstractmethod
import urllib.request
import os
import uuid
from app.core.logging import get_logger

logger = get_logger(__name__)

class ImageAdapter(ABC):
    @abstractmethod
    async def generate_image(self, prompt: str, output_path: str) -> str:
        pass


class FluxAdapter(ImageAdapter):
    async def generate_image(self, prompt: str, output_path: str) -> str:
        # TODO: Implement Fal.ai / Replicate FLUX API call here
        logger.info("FluxAdapter generating image", prompt=prompt)
        raise NotImplementedError("Flux API key not configured.")


class StableDiffusionAdapter(ImageAdapter):
    async def generate_image(self, prompt: str, output_path: str) -> str:
        # TODO: Implement Stability AI API call here
        logger.info("StableDiffusionAdapter generating image", prompt=prompt)
        raise NotImplementedError("Stability API key not configured.")


class MockImageAdapter(ImageAdapter):
    """
    Downloads a high-quality placeholder image for MVP testing.
    """
    async def generate_image(self, prompt: str, output_path: str) -> str:
        logger.info("MockImageAdapter downloading placeholder", prompt=prompt)
        # Using a reliable placeholder service
        # Keyword-based fetching (e.g. nature, technology) could be extracted from prompt,
        # but for stability we just download a static cinematic placeholder.
        url = "https://picsum.photos/1920/1080"
        
        try:
            urllib.request.urlretrieve(url, output_path)
            return output_path
        except Exception as e:
            logger.error("Failed to download placeholder", error=str(e))
            # Fallback: create an empty file so the pipeline doesn't crash
            with open(output_path, "wb") as f:
                f.write(b"")
            return output_path


class ImageEngine:
    """
    Provides the configured ImageAdapter.
    """
    def __init__(self, provider: str = "mock"):
        self.provider = provider

    def get_adapter(self) -> ImageAdapter:
        if self.provider == "flux":
            return FluxAdapter()
        elif self.provider == "sd":
            return StableDiffusionAdapter()
        return MockImageAdapter()
