"""
Replicate adapter for AI image generation using Flux models.
"""

import asyncio
from typing import Optional
from dataclasses import dataclass

try:
    import replicate
except ImportError:
    replicate = None

from infrastructure.config.settings import settings


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
        if settings.replicate_api_token and replicate:
            self._client = replicate.Client(api_token=settings.replicate_api_token)
        else:
            self._client = None
        self._model = settings.replicate_model

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

            # Replicate returns either a URL string or a list with one URL
            if isinstance(output, list) and len(output) > 0:
                image_url = output[0]
            else:
                image_url = str(output)

            return GeneratedImage(
                url=image_url,
                prompt=prompt,
                width=width,
                height=height,
                model=self._model,
                style=style,
            )

        except Exception as e:
            # Graceful error handling - return mock data on error
            print(f"Error generating image with Replicate: {e}")
            return self._mock_image(prompt, width, height, style)

    def _run_model(self, prompt: str, width: int, height: int):
        """
        Run the Replicate model synchronously.

        This method is called in a thread pool by generate_image.
        """
        input_params = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_outputs": 1,
            "aspect_ratio": f"{width}:{height}",
            "output_format": "jpg",
            "output_quality": 90,
        }

        return self._client.run(
            self._model,
            input=input_params,
        )

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
            "photographic": "professional photograph, high detail, sharp focus, realistic lighting",
            "artistic": "artistic illustration, creative, expressive, vibrant colors",
            "minimalist": "minimalist design, clean lines, simple composition, elegant",
            "dramatic": "dramatic lighting, high contrast, cinematic, moody atmosphere",
            "vintage": "vintage style, retro aesthetic, film grain, nostalgic",
            "modern": "modern design, sleek, contemporary, polished",
            "abstract": "abstract art, geometric shapes, conceptual, creative interpretation",
            "watercolor": "watercolor painting style, soft edges, flowing colors, artistic",
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
