"""Application settings and configuration."""
import json
import secrets
from functools import lru_cache
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

def _generate_dev_secret() -> str:
    """Generate a random secret for development use.

    Tokens issued with this key won't survive server restarts, which is
    acceptable in development.  Production **must** set explicit secrets
    via environment variables — the startup validator enforces this.
    """
    return secrets.token_urlsafe(32)


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
    db_pool_size: int = 20
    db_max_overflow: int = 40

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        """Auto-convert Railway's postgresql:// to postgresql+asyncpg://."""
        if isinstance(v, str):
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    # Redis (for background tasks and caching)
    redis_url: str = "redis://localhost:6379/0"

    # Authentication / JWT
    secret_key: str = ""
    jwt_secret_key: str = ""
    @field_validator("secret_key", "jwt_secret_key", mode="before")
    @classmethod
    def fill_empty_secret(cls, v: str) -> str:
        """Generate a random secret when no value is provided.

        This keeps development functional without a .env file while ensuring
        production never silently falls back to a guessable default.
        """
        if not v:
            return _generate_dev_secret()
        return v

    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # CORS - stored as str to prevent pydantic-settings auto-JSON-parse failures
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins into a list, stripping trailing slashes."""
        v = self.cors_origins.strip()
        if v.startswith("["):
            try:
                origins = json.loads(v)
                return [o.rstrip("/") for o in origins]
            except json.JSONDecodeError:
                pass
        return [origin.strip().strip("'\"").rstrip("/") for origin in v.split(",") if origin.strip()]

    # Anthropic (AI Content Generation)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 4096
    anthropic_timeout: int = 300

    # Replicate (Image Generation)
    replicate_api_token: Optional[str] = None
    replicate_model: str = "ideogram-ai/ideogram-v3-turbo"

    # Resend (Email)
    resend_api_key: Optional[str] = None
    resend_from_email: str = "noreply@astats.app"

    # LemonSqueezy (Payments)
    lemonsqueezy_api_key: Optional[str] = None
    lemonsqueezy_store_id: Optional[str] = None
    lemonsqueezy_webhook_secret: Optional[str] = None
    lemonsqueezy_variant_starter_monthly: Optional[str] = None
    lemonsqueezy_variant_starter_yearly: Optional[str] = None
    lemonsqueezy_variant_professional_monthly: Optional[str] = None
    lemonsqueezy_variant_professional_yearly: Optional[str] = None
    lemonsqueezy_variant_enterprise_monthly: Optional[str] = None
    lemonsqueezy_variant_enterprise_yearly: Optional[str] = None

    # Google (OAuth & Search Console)
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://localhost:3000/analytics/callback"

    # Twitter/X OAuth 2.0
    twitter_client_id: Optional[str] = None
    twitter_client_secret: Optional[str] = None
    twitter_redirect_uri: str = "http://localhost:8000/api/v1/social/twitter/callback"

    # LinkedIn OAuth 2.0
    linkedin_client_id: Optional[str] = None
    linkedin_client_secret: Optional[str] = None
    linkedin_redirect_uri: str = "http://localhost:8000/api/v1/social/linkedin/callback"

    # Facebook/Instagram OAuth
    facebook_app_id: Optional[str] = None
    facebook_app_secret: Optional[str] = None
    facebook_redirect_uri: str = "http://localhost:8000/api/v1/social/facebook/callback"

    # ChromaDB (Vector Store)
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_persist_directory: str = "./data/chroma"
    chroma_collection_prefix: str = "knowledge_vault"

    # Embeddings
    embedding_model: str = "text-embedding-3-small"  # OpenAI model
    openai_api_key: Optional[str] = None  # For embeddings

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

    def validate_production_secrets(self) -> None:
        """Validate that production secrets and critical API keys are configured.

        Called automatically by get_settings().  In production/staging the
        app refuses to start unless explicit, strong secrets are provided
        via environment variables.
        """
        if self.environment in ("production", "staging"):
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be set to at least 32 characters in production!")
            if len(self.jwt_secret_key) < 32:
                raise ValueError("JWT_SECRET_KEY must be set to at least 32 characters in production!")
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is required in production!")
            if not self.lemonsqueezy_api_key:
                raise ValueError("LEMONSQUEEZY_API_KEY is required in production!")
            if not self.lemonsqueezy_webhook_secret:
                raise ValueError("LEMONSQUEEZY_WEBHOOK_SECRET is required in production!")

        # INFRA-10: OAuth redirect URIs must be https:// non-localhost in production
        if self.environment == "production":
            from urllib.parse import urlparse as _urlparse
            _localhost_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
            for _uri_name, _uri_val in [
                ("GOOGLE_REDIRECT_URI", self.google_redirect_uri),
                ("TWITTER_REDIRECT_URI", self.twitter_redirect_uri),
                ("LINKEDIN_REDIRECT_URI", self.linkedin_redirect_uri),
                ("FACEBOOK_REDIRECT_URI", self.facebook_redirect_uri),
            ]:
                _parsed = _urlparse(_uri_val)
                if _parsed.scheme != "https" or (_parsed.hostname or "") in _localhost_hosts:
                    raise ValueError(
                        f"{_uri_name} must be an https:// non-localhost URL in production "
                        f"(got: {_uri_val!r})"
                    )

            # INFRA-15: Ensure database_echo is off in production to prevent SQL leaking into logs
            if self.database_echo:
                raise ValueError(
                    "DATABASE_ECHO must be False in production to prevent SQL queries in logs"
                )

            # INFRA-12: Warn about potential connection pool exhaustion
            import logging as _logging
            _pool_total = self.db_pool_size * self.workers + self.db_max_overflow * self.workers
            if _pool_total > 200:
                _logging.getLogger(__name__).warning(
                    "INFRA-12: Potential DB connection pool exhaustion — "
                    "%d workers × pool_size=%d + max_overflow=%d = up to %d connections. "
                    "Verify your DB allows this many connections.",
                    self.workers, self.db_pool_size, self.db_max_overflow, _pool_total,
                )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Automatically validates that production/staging deployments have
    proper secrets configured — the app will refuse to start otherwise.
    """
    s = Settings()
    s.validate_production_secrets()
    return s


# Global settings instance
settings = get_settings()
