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
    def __init__(self):
        from app.core.config import settings
        self.api_key = settings.FAL_API_KEY if hasattr(settings, 'FAL_API_KEY') else None

    async def generate_image(self, prompt: str, output_path: str) -> str:
        if not self.api_key:
            logger.error("fal_missing_key")
            raise RuntimeError("FAL API Key is not configured.")
            
        import httpx
        url = "https://fal.run/fal-ai/flux/schnell"
        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "prompt": prompt,
            "image_size": "landscape_16_9",
            "num_inference_steps": 4
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=data, headers=headers)
            resp.raise_for_status()
            result = resp.json()
            image_url = result["images"][0]["url"]
            
            # Download the resulting image to the output_path
            image_resp = await client.get(image_url)
            image_resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(image_resp.content)
            
            return output_path


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
