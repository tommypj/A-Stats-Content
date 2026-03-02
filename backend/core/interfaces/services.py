"""Service interfaces for external integrations."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass


@dataclass
class GenerationResult:
    """Result of AI content generation."""

    content: str
    tokens_used: int
    model: str
    generation_time: float


@dataclass
class ImageResult:
    """Result of image generation."""

    url: str
    width: int
    height: int
    prompt: str


class AIService(ABC):
    """Abstract service for AI content generation."""

    @abstractmethod
    async def generate_article(
        self,
        outline_title: str,
        keyword: str,
        brief: str | None = None,
        persona_intensity: str = "balanced",
        target_words: int = 1500,
        context: str | None = None,
    ) -> GenerationResult:
        """Generate a full article from outline."""
        ...

    @abstractmethod
    async def generate_article_stream(
        self,
        outline_title: str,
        keyword: str,
        brief: str | None = None,
        persona_intensity: str = "balanced",
        target_words: int = 1500,
        context: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Generate article with streaming response."""
        ...

    @abstractmethod
    async def generate_social_echo(
        self,
        article_content: str,
        persona_intensity: str = "balanced",
    ) -> dict:
        """Generate social media content from article."""
        ...

    @abstractmethod
    async def evaluate_authenticity(
        self,
        content: str,
        persona_intensity: str = "balanced",
    ) -> float:
        """Evaluate content authenticity score."""
        ...


class ImageService(ABC):
    """Abstract service for image generation."""

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
    ) -> ImageResult:
        """Generate an image from prompt."""
        ...

    @abstractmethod
    async def generate_alt_text(
        self,
        image_url: str,
    ) -> str:
        """Generate SEO alt text for image using vision."""
        ...

    @abstractmethod
    async def optimize_image(
        self,
        image_path: str,
        output_format: str = "webp",
        quality: int = 85,
    ) -> str:
        """Optimize and convert image."""
        ...


class EmailService(ABC):
    """Abstract service for email communication."""

    @abstractmethod
    async def send_verification_email(
        self,
        to_email: str,
        verification_url: str,
    ) -> bool:
        """Send email verification link."""
        ...

    @abstractmethod
    async def send_password_reset(
        self,
        to_email: str,
        reset_url: str,
    ) -> bool:
        """Send password reset link."""
        ...

    @abstractmethod
    async def send_weekly_summary(
        self,
        to_email: str,
        summary_data: dict,
    ) -> bool:
        """Send weekly performance summary."""
        ...


class PaymentService(ABC):
    """Abstract service for payment processing."""

    @abstractmethod
    async def create_customer(
        self,
        email: str,
        name: str | None = None,
    ) -> str:
        """Create a customer and return customer ID."""
        ...

    @abstractmethod
    async def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create checkout session and return URL."""
        ...

    @abstractmethod
    async def create_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> str:
        """Create billing portal session and return URL."""
        ...

    @abstractmethod
    async def handle_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> dict:
        """Process webhook event."""
        ...
