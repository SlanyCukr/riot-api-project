"""Configuration settings for the Riot API application."""

from __future__ import annotations

import os
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database Configuration
    postgres_db: str = Field(default="riot_api_db")
    postgres_user: str = Field(default="riot_api_user")
    postgres_password: str = Field(default="dev_password")
    postgres_host: str = Field(default="postgres")
    postgres_port: int = Field(default=5432)

    @property
    def database_url(self) -> str:
        """Construct async database URL from components."""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Application Configuration
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # CORS Configuration
    cors_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    @property
    def environment(self) -> str:  # noqa: vulture
        """Get current environment from ENVIRONMENT variable."""
        env = os.getenv("ENVIRONMENT", "").lower()
        return env if env in ["dev", "production"] else "dev"  # Safe default

    # JWT Authentication Configuration
    jwt_secret_key: str = Field(
        default="dev_secret_key_please_change_in_production",
        description="Secret key for JWT token signing - MUST be changed in production",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=10080,  # 7 days
        description="JWT access token expiration time in minutes",
    )

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT secret key meets security requirements.

        Enforces:
        - Minimum length of 32 characters (256 bits for HS256 per RFC 7518)
        - No default/placeholder values in production
        - Fails fast on startup with clear error messages

        Raises:
            ValueError: If secret is weak and environment is production
        """
        # Check if running in production
        env = os.getenv("ENVIRONMENT", "").lower()
        is_production = env == "production"

        # Check for default/placeholder secrets
        weak_indicators = ["dev_secret", "please_change", "changeme", "secret_key"]
        is_weak = any(indicator in v.lower() for indicator in weak_indicators)

        if is_weak:
            if is_production:
                raise ValueError(
                    "Production deployment detected with default/weak JWT secret! "
                    "Generate a strong secret using: python -c 'import secrets; print(secrets.token_hex(32))' "
                    "and set it via JWT_SECRET_KEY environment variable."
                )
            # Warn in development but allow
            import sys

            print(
                "⚠️  WARNING: Using default JWT secret in development. "
                "Generate a production secret before deployment!",
                file=sys.stderr,
            )

        # Enforce minimum length (32 chars = 256 bits)
        if len(v) < 32:
            if is_production:
                raise ValueError(
                    f"JWT secret must be at least 32 characters (256 bits). "
                    f"Current length: {len(v)} characters. "
                    f"Generate a strong secret using: python -c 'import secrets; print(secrets.token_hex(32))'"
                )
            # Warn in development but allow
            import sys

            print(
                f"⚠️  WARNING: JWT secret is too short ({len(v)} chars). "
                f"Minimum recommended: 32 characters. Generate with: python -c 'import secrets; print(secrets.token_hex(32))'",
                file=sys.stderr,
            )

        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_prefix="",  # No prefix for environment variables
        extra="forbid",  # Forbid extra fields for better type safety
    )


def get_settings() -> Settings:
    """Get application settings instance."""
    # Pydantic v2 will automatically load from environment variables
    # This allows lazy loading when the module is imported
    return Settings()


# Create a global settings instance lazily
settings: Settings | None = None


def get_global_settings() -> Settings:
    """Get or create the global settings instance."""
    global settings
    if settings is None:
        settings = get_settings()
    return settings


async def get_riot_api_key(db: AsyncSession) -> str:
    """Get Riot API key from database only.

    NOTE: RIOT_API_KEY environment variable is no longer supported.
    Set API key via web UI at /settings or directly in database.

    :param db: Database session
    :returns: Riot API key from database
    :raises ValueError: If API key not configured in database
    """
    from sqlalchemy import select
    from app.features.settings.models import SystemSetting

    stmt = select(SystemSetting).where(SystemSetting.key == "riot_api_key")
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()

    if not setting or not setting.value:
        raise ValueError(
            "Riot API key not configured! Set it via web UI at /settings or database:\n"
            "INSERT INTO jobs.system_settings (key, value, category, is_sensitive) "
            "VALUES ('riot_api_key', 'YOUR_KEY', 'riot_api', true);"
        )

    return setting.value
