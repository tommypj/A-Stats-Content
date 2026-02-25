"""Subscription domain entities."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class SubscriptionTier(str, Enum):
    """Available subscription tiers."""
    FREE = "free"
    PRO = "pro"
    ELITE = "elite"


class BillingInterval(str, Enum):
    """Billing interval options."""
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass
class TierFeatures:
    """Features available in each tier."""

    tier: SubscriptionTier

    # Limits
    articles_per_month: int = 0
    social_posts_per_month: int = 0
    images_per_month: int = 0
    knowledge_docs: int = 0

    # Features
    gsc_integration: bool = False
    wordpress_integration: bool = False
    api_access: bool = False
    priority_support: bool = False
    white_label: bool = False

    @classmethod
    def for_tier(cls, tier: SubscriptionTier) -> "TierFeatures":
        """Get features for a specific tier."""
        if tier == SubscriptionTier.FREE:
            return cls(
                tier=tier,
                articles_per_month=3,
                social_posts_per_month=5,
                images_per_month=5,
                knowledge_docs=0,
                gsc_integration=False,
                wordpress_integration=False,
            )
        elif tier == SubscriptionTier.PRO:
            return cls(
                tier=tier,
                articles_per_month=30,
                social_posts_per_month=60,
                images_per_month=30,
                knowledge_docs=10,
                gsc_integration=True,
                wordpress_integration=True,
            )
        else:  # ELITE
            return cls(
                tier=tier,
                articles_per_month=999,  # Unlimited
                social_posts_per_month=999,
                images_per_month=100,
                knowledge_docs=50,
                gsc_integration=True,
                wordpress_integration=True,
                api_access=True,
                priority_support=True,
            )


@dataclass
class Subscription:
    """User subscription entity."""

    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)

    # Stripe integration
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None

    # Subscription details
    tier: SubscriptionTier = SubscriptionTier.FREE
    interval: BillingInterval = BillingInterval.MONTHLY
    status: str = "active"  # active, canceled, past_due, trialing

    # Dates
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None

    # Usage tracking
    articles_used: int = 0
    social_posts_used: int = 0
    images_used: int = 0

    # Credits (for pay-as-you-go)
    credits_balance: int = 0

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if isinstance(self.id, str):
            self.id = UUID(self.id)
        if isinstance(self.user_id, str):
            self.user_id = UUID(self.user_id)
        if isinstance(self.tier, str):
            self.tier = SubscriptionTier(self.tier)
        if isinstance(self.interval, str):
            self.interval = BillingInterval(self.interval)

    @property
    def features(self) -> TierFeatures:
        """Get features for current tier."""
        return TierFeatures.for_tier(self.tier)

    def can_generate_article(self) -> bool:
        """Check if user can generate another article this period."""
        return self.articles_used < self.features.articles_per_month

    def can_generate_social(self) -> bool:
        """Check if user can generate another social post."""
        return self.social_posts_used < self.features.social_posts_per_month

    def can_generate_image(self) -> bool:
        """Check if user can generate another image."""
        return self.images_used < self.features.images_per_month
