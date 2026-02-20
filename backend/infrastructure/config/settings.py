"""Application settings and configuration."""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "A-Stats Engine"
    app_version: str = "2.0.0"
    debug: bool = False
    environment: str = "development"  # development, staging, production

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/astats"
    database_echo: bool = False

    # Redis (for background tasks and caching)
    redis_url: str = "redis://localhost:6379/0"

    # Authentication / JWT
    secret_key: str = "change-me-in-production-use-secrets-gen"
    jwt_secret_key: str = "change-me-in-production-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Anthropic (AI Content Generation)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 4096

    # Replicate (Image Generation)
    replicate_api_token: Optional[str] = None
    replicate_model: str = "black-forest-labs/flux-1.1-pro"

    # Resend (Email)
    resend_api_key: Optional[str] = None
    resend_from_email: str = "noreply@astats.app"

    # Stripe (Payments)
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_pro_monthly: Optional[str] = None
    stripe_price_pro_yearly: Optional[str] = None
    stripe_price_elite_monthly: Optional[str] = None
    stripe_price_elite_yearly: Optional[str] = None

    # Google (OAuth & Search Console)
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://localhost:8000/api/v1/gsc/callback"

    # ChromaDB (Vector Store)
    chroma_persist_directory: str = "./data/chroma"
    chroma_collection_name: str = "knowledge_vault"

    # Storage
    storage_type: str = "local"  # local, s3
    storage_local_path: str = "./data/uploads"
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None

    # Frontend URL (for email links)
    frontend_url: str = "http://localhost:3000"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
