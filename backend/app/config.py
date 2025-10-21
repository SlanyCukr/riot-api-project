"""Configuration settings for the Riot API application."""

from __future__ import annotations

import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Riot API Configuration
    riot_api_key: str = Field(default="dev_api_key")
    riot_region: str = Field(default="europe")
    riot_platform: str = Field(default="eun1")

    # Database Configuration
    postgres_password: str = Field(default="dev_password")
    database_url: str = Field(
        default="postgresql+asyncpg://riot_api_user:dev_password@localhost/riot_api_db"
    )

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

    # Database Connection Pool Settings
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=20)
    db_pool_timeout: int = Field(default=30)
    db_pool_recycle: int = Field(default=1800)

    # Job Scheduler Configuration
    job_scheduler_enabled: bool = Field(default=False)

    # Player Tracking Configuration
    max_tracked_players: int = Field(default=100)

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


async def get_riot_api_key(db: Optional[AsyncSession] = None) -> str:
    """
    Get the Riot API key from database or environment.

    Priority:
    1. Database (runtime configuration) - if db session provided
    2. Environment variable
    3. Default value

    Args:
        db: Optional database session. If provided, will query database first.
            If not provided, uses environment variable only.
    """
    if db is not None:
        try:
            from sqlalchemy import select
            from sqlalchemy.exc import SQLAlchemyError, DatabaseError
            from .models.settings import SystemSetting

            stmt = select(SystemSetting).where(SystemSetting.key == "riot_api_key")
            result = await db.execute(stmt)
            setting = result.scalar_one_or_none()

            if setting:
                return setting.value
        except (DatabaseError, SQLAlchemyError):
            # Database error - fall back to environment variable
            pass

    settings = get_global_settings()
    return settings.riot_api_key
