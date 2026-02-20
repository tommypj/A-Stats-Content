"""Content domain entities."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class ContentStatus(str, Enum):
    """Content lifecycle status."""
    DRAFT = "draft"
    GENERATING = "generating"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class JourneyPhase(str, Enum):
    """SEO Journey Phase (Healing Stage)."""
    DISCOVERY = "discovery"
    VALIDATION = "validation"
    ACTION = "action"


class PersonaIntensity(str, Enum):
    """Therapeutic persona intensity levels."""
    SUPPORTIVE = "supportive"  # Warm, gentle
    BALANCED = "balanced"      # Professional yet caring
    DIRECT = "direct"          # Clear, action-oriented


@dataclass
class Outline:
    """Content outline - the foundation for article generation."""

    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)

    # Core fields
    title: str = ""
    keyword: str = ""
    brief: Optional[str] = None
    status: ContentStatus = ContentStatus.DRAFT

    # SEO metadata
    journey_phase: Optional[JourneyPhase] = None
    search_volume: Optional[int] = None
    current_position: Optional[float] = None
    impressions: Optional[int] = None

    # Generation settings
    language: str = "en"
    persona_intensity: PersonaIntensity = PersonaIntensity.BALANCED
    target_word_count: int = 1500

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None

    # WordPress integration
    wordpress_post_id: Optional[int] = None
    wordpress_url: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.id, str):
            self.id = UUID(self.id)
        if isinstance(self.user_id, str):
            self.user_id = UUID(self.user_id)
        if isinstance(self.status, str):
            self.status = ContentStatus(self.status)
        if isinstance(self.journey_phase, str):
            self.journey_phase = JourneyPhase(self.journey_phase)
        if isinstance(self.persona_intensity, str):
            self.persona_intensity = PersonaIntensity(self.persona_intensity)


@dataclass
class Article:
    """Generated article content."""

    id: UUID = field(default_factory=uuid4)
    outline_id: UUID = field(default_factory=uuid4)

    # Content
    content_markdown: str = ""
    content_html: str = ""
    meta_description: str = ""

    # Sections (H2 headings)
    sections: list[dict] = field(default_factory=list)

    # Featured image
    featured_image_url: Optional[str] = None
    featured_image_alt: Optional[str] = None

    # Quality metrics
    word_count: int = 0
    authenticity_score: Optional[float] = None

    # Generation metadata
    model_used: str = "claude-sonnet-4-20250514"
    tokens_used: int = 0
    generation_time_seconds: float = 0.0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if isinstance(self.id, str):
            self.id = UUID(self.id)
        if isinstance(self.outline_id, str):
            self.outline_id = UUID(self.outline_id)
