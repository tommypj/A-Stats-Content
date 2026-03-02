"""User domain entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class UserRole(StrEnum):
    """User roles in the system."""

    USER = "user"
    ADMIN = "admin"
    SUPERUSER = "superuser"


@dataclass
class User:
    """User domain entity - core business object."""

    id: UUID = field(default_factory=uuid4)
    email: str = ""
    hashed_password: str = ""
    full_name: str = ""
    role: UserRole = UserRole.USER
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Optional integrations
    google_id: str | None = None
    gsc_refresh_token: str | None = None
    wordpress_url: str | None = None
    wordpress_username: str | None = None
    wordpress_app_password: str | None = None

    # Subscription
    subscription_tier: str = "free"
    credits_remaining: int = 0

    def __post_init__(self):
        if isinstance(self.id, str):
            self.id = UUID(self.id)
        if isinstance(self.role, str):
            self.role = UserRole(self.role)

    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.role in (UserRole.ADMIN, UserRole.SUPERUSER)

    @property
    def is_superuser(self) -> bool:
        """Check if user is superuser."""
        return self.role == UserRole.SUPERUSER

    def can_access_feature(self, feature: str) -> bool:
        """Check if user's subscription allows access to a feature."""
        # Feature access logic based on tier
        free_features = {"dashboard", "content_view", "settings"}
        pro_features = free_features | {"content_generate", "social_echo", "gsc_connect"}
        elite_features = pro_features | {"knowledge_vault", "api_access", "priority_support"}

        if self.subscription_tier == "elite":
            return feature in elite_features
        elif self.subscription_tier == "pro":
            return feature in pro_features
        return feature in free_features
