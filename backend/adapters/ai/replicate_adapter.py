"""
Replicate adapter for AI image generation using Flux models.
"""

import asyncio
import logging
from typing import Optional
from dataclasses import dataclass

try:
    import replicate
except ImportError:
    replicate = None

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class GeneratedImage:
    """Generated image result."""

    url: str
    prompt: str
    width: int
    height: int
    model: str
    style: Optional[str] = None


class ReplicateImageService:
    """AI image generation service using Replicate Flux models."""

    def __init__(self):
        self._model = settings.replicate_model
        if not replicate:
            logger.warning("replicate package not installed — image generation will use mock mode")
            self._client = None
        elif not settings.replicate_api_token:
            logger.warning("REPLICATE_API_TOKEN not set — image generation will use mock mode")
            self._client = None
        else:
            self._client = replicate.Client(api_token=settings.replicate_api_token)
            logger.info(f"Replicate client initialized with model: {self._model}")

    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        style: Optional[str] = None,
    ) -> GeneratedImage:
        """
        Generate an image using Replicate Flux model.

        Args:
            prompt: Text description of the image to generate
            width: Image width in pixels (default: 1024)
            height: Image height in pixels (default: 1024)
            style: Optional style modifier (e.g., "photographic", "artistic", "minimalist")

        Returns:
            GeneratedImage with URL and metadata
        """
        if not self._client:
            # Return mock data for development when no API key is configured
            return self._mock_image(prompt, width, height, style)

        try:
            # Enhance prompt with style if provided
            enhanced_prompt = self._enhance_prompt(prompt, style)

            # Run Replicate model in a thread pool to avoid blocking
            # Replicate's run() is synchronous, so we use asyncio.to_thread
            output = await asyncio.to_thread(
                self._run_model,
                enhanced_prompt,
                width,
                height,
            )

            # Replicate models return various types: URL string, list of URLs, or FileOutput
            if isinstance(output, list) and len(output) > 0:
                image_url = str(output[0])
            elif hasattr(output, 'url'):
                image_url = output.url
            else:
                image_url = str(output)

            logger.info(f"Generated image URL: {image_url}")

            return GeneratedImage(
                url=image_url,
                prompt=prompt,
                width=width,
                height=height,
                model=self._model,
                style=style,
            )

        except Exception as e:
            logger.error(f"Replicate image generation failed: {e}", exc_info=True)
            raise

    def _run_model(self, prompt: str, width: int, height: int):
        """
        Run the Replicate model synchronously.

        This method is called in a thread pool by generate_image.
        """
        # Ideogram V3 Turbo on Replicate accepts aspect_ratio as "W:H" strings
        # Valid values: "1:3","3:1","1:2","2:1","9:16","16:9","10:16","16:10","2:3","3:2","3:4","4:3","4:5","5:4","1:1"
        ratio = width / height
        if abs(ratio - 1.0) < 0.05:
            aspect_ratio = "1:1"
        elif abs(ratio - (4/3)) < 0.05:
            aspect_ratio = "4:3"
        elif abs(ratio - (3/4)) < 0.05:
            aspect_ratio = "3:4"
        elif abs(ratio - (16/9)) < 0.05:
            aspect_ratio = "16:9"
        elif abs(ratio - (9/16)) < 0.05:
            aspect_ratio = "9:16"
        elif abs(ratio - (3/2)) < 0.05:
            aspect_ratio = "3:2"
        elif abs(ratio - (2/3)) < 0.05:
            aspect_ratio = "2:3"
        elif abs(ratio - (4/5)) < 0.05:
            aspect_ratio = "4:5"
        elif abs(ratio - (5/4)) < 0.05:
            aspect_ratio = "5:4"
        elif ratio > 1.5:
            aspect_ratio = "16:9"
        elif ratio < 0.67:
            aspect_ratio = "9:16"
        else:
            aspect_ratio = "1:1"

        input_params = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
        }

        logger.info(f"Calling Replicate model {self._model} with aspect_ratio={aspect_ratio}")

        output = self._client.run(
            self._model,
            input=input_params,
        )

        logger.info(f"Replicate output type: {type(output)}, value: {output}")
        return output

    def _enhance_prompt(self, prompt: str, style: Optional[str] = None) -> str:
        """
        Enhance the prompt with style modifiers.

        Args:
            prompt: Original prompt
            style: Style modifier to apply

        Returns:
            Enhanced prompt with style guidance
        """
        if not style:
            return prompt

        style_modifiers = {
            "realistic": "ultra realistic, photorealistic, natural lighting, real-world textures, no AI artifacts, lifelike details",
            "photographic": "professional photography, realistic, sharp focus",
            "artistic": "artistic illustration, creative, vibrant colors",
            "minimalist": "minimalist design, clean lines, simple composition",
            "dramatic": "dramatic lighting, high contrast, cinematic",
            "vintage": "vintage aesthetic, retro, film grain",
            "modern": "modern design, sleek, contemporary",
            "abstract": "abstract art, geometric, conceptual",
            "watercolor": "watercolor painting, soft edges, flowing colors",
        }

        modifier = style_modifiers.get(style.lower(), style)
        return f"{prompt}, {modifier}"

    def _mock_image(
        self,
        prompt: str,
        width: int,
        height: int,
        style: Optional[str] = None,
    ) -> GeneratedImage:
        """
        Generate mock image data for development.

        Returns a placeholder image URL from picsum.photos.
        """
        # Use picsum.photos for placeholder images with the specified dimensions
        placeholder_url = f"https://picsum.photos/{width}/{height}"

        return GeneratedImage(
            url=placeholder_url,
            prompt=prompt,
            width=width,
            height=height,
            model=self._model,
            style=style,
        )


# Singleton instance
image_ai_service = ReplicateImageService()
