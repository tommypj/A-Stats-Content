"""
Replicate adapter for AI image generation using Ideogram V3 Turbo.
"""

import asyncio
import logging
import random
from dataclasses import dataclass

try:
    import replicate
except ImportError:
    replicate = None

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


async def _retry_with_backoff(coro_factory, max_retries=3, base_delay=1.0):
    """Retry an async operation with exponential backoff + jitter."""
    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except Exception as e:
            error_str = str(e).lower()
            is_transient = any(
                k in error_str
                for k in [
                    "rate_limit",
                    "429",
                    "500",
                    "502",
                    "503",
                    "504",
                    "overloaded",
                    "connection",
                    "timeout",
                ]
            )
            if not is_transient or attempt == max_retries:
                raise
            delay = base_delay * (2**attempt) + random.uniform(0, 1)
            logger.warning(
                "Transient API error (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1,
                max_retries,
                delay,
                str(e),
            )
            await asyncio.sleep(delay)


@dataclass
class GeneratedImage:
    """Generated image result."""

    url: str
    prompt: str
    width: int
    height: int
    model: str
    style: str | None = None


# Map our frontend styles to Ideogram V3 native parameters.
# style_type: "None", "Auto", "General", "Realistic", "Design"
# style_preset: 60+ presets like "Oil Painting", "Watercolor", "Pop Art", etc.
STYLE_CONFIG = {
    "realistic": {
        "style_type": "Realistic",
        "prompt_suffix": "ultra realistic, photorealistic, natural skin textures, natural lighting, lifelike details",
    },
    "photographic": {
        "style_type": "Realistic",
        "style_preset": "Photography",
        "prompt_suffix": "professional DSLR photography, sharp focus, natural depth of field",
    },
    "artistic": {
        "style_type": "General",
        "prompt_suffix": "artistic illustration, creative, vibrant colors",
    },
    "minimalist": {
        "style_type": "Design",
        "prompt_suffix": "minimalist design, clean lines, simple composition",
    },
    "dramatic": {
        "style_type": "Realistic",
        "prompt_suffix": "dramatic lighting, high contrast, cinematic mood",
    },
    "vintage": {
        "style_type": "General",
        "style_preset": "Vintage",
        "prompt_suffix": "vintage aesthetic, retro color grading, film grain",
    },
    "modern": {
        "style_type": "Design",
        "prompt_suffix": "modern design, sleek, contemporary aesthetic",
    },
    "abstract": {
        "style_type": "General",
        "prompt_suffix": "abstract art, geometric forms, conceptual",
    },
    "watercolor": {
        "style_type": "General",
        "style_preset": "Watercolor",
        "prompt_suffix": "watercolor painting, soft edges, flowing colors",
    },
}


class ReplicateImageService:
    """AI image generation service using Replicate Ideogram V3 Turbo."""

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
        style: str | None = None,
    ) -> GeneratedImage:
        """
        Generate an image using Ideogram V3 Turbo via Replicate.

        Args:
            prompt: Text description of the image to generate
            width: Image width in pixels (default: 1024)
            height: Image height in pixels (default: 1024)
            style: Style key (e.g., "realistic", "photographic", "artistic")

        Returns:
            GeneratedImage with URL and metadata
        """
        if not self._client:
            return self._mock_image(prompt, width, height, style)

        try:
            # Get style configuration
            style_cfg = STYLE_CONFIG.get(style.lower() if style else "", {})

            # Enhance prompt with style suffix
            enhanced_prompt = prompt
            if style_cfg.get("prompt_suffix"):
                enhanced_prompt = f"{prompt}, {style_cfg['prompt_suffix']}"

            # Run Replicate model in a thread pool (synchronous client)
            # Capture locals for lambda closure
            _prompt_cap = enhanced_prompt
            _width_cap = width
            _height_cap = height
            _style_cfg_cap = style_cfg
            output = await _retry_with_backoff(
                lambda: asyncio.wait_for(
                    asyncio.to_thread(
                        self._run_model,
                        _prompt_cap,
                        _width_cap,
                        _height_cap,
                        _style_cfg_cap,
                    ),
                    timeout=300,  # 5 minute timeout
                )
            )

            # Replicate models return various types: URL string, list of URLs, or FileOutput
            if isinstance(output, list) and len(output) > 0:
                image_url = str(output[0])
            elif hasattr(output, "url"):
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

    def _run_model(self, prompt: str, width: int, height: int, style_cfg: dict):
        """
        Run the Replicate model synchronously.

        This method is called in a thread pool by generate_image.
        """
        # Calculate aspect ratio from dimensions
        ratio = width / height
        if abs(ratio - 1.0) < 0.05:
            aspect_ratio = "1:1"
        elif abs(ratio - (4 / 3)) < 0.05:
            aspect_ratio = "4:3"
        elif abs(ratio - (3 / 4)) < 0.05:
            aspect_ratio = "3:4"
        elif abs(ratio - (16 / 9)) < 0.05:
            aspect_ratio = "16:9"
        elif abs(ratio - (9 / 16)) < 0.05:
            aspect_ratio = "9:16"
        elif abs(ratio - (3 / 2)) < 0.05:
            aspect_ratio = "3:2"
        elif abs(ratio - (2 / 3)) < 0.05:
            aspect_ratio = "2:3"
        elif abs(ratio - (4 / 5)) < 0.05:
            aspect_ratio = "4:5"
        elif abs(ratio - (5 / 4)) < 0.05:
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

        # Apply Ideogram native style_type parameter (Realistic, General, Design)
        if style_cfg.get("style_type"):
            input_params["style_type"] = style_cfg["style_type"]

        # Apply Ideogram native style_preset (Watercolor, Photography, Vintage, etc.)
        if style_cfg.get("style_preset"):
            input_params["style_preset"] = style_cfg["style_preset"]

        logger.info(
            f"Calling Replicate model {self._model} with "
            f"aspect_ratio={aspect_ratio}, style_type={style_cfg.get('style_type')}, "
            f"style_preset={style_cfg.get('style_preset')}"
        )

        output = self._client.run(
            self._model,
            input=input_params,
        )

        logger.info(f"Replicate output type: {type(output)}, value: {output}")
        return output

    def _mock_image(
        self,
        prompt: str,
        width: int,
        height: int,
        style: str | None = None,
    ) -> GeneratedImage:
        """
        Generate mock image data for development.

        Returns a placeholder image URL from picsum.photos.
        """
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
