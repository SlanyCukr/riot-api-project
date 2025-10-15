"""Configuration settings for the Riot API application."""

from __future__ import annotations

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
    postgres_db: str = Field(default="riot_api_db")
    postgres_user: str = Field(default="riot_api_user")
    postgres_password: str = Field(default="dev_password")
    database_url: str = Field(
        default="postgresql+asyncpg://riot_api_user:dev_password@localhost/riot_api_db"
    )

    # Application Configuration
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # Frontend Configuration
    api_url: str = Field(default="http://localhost:8000")

    # CORS Configuration
    cors_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    # Database Connection Pool Settings
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=20)
    db_pool_timeout: int = Field(default=30)
    db_pool_recycle: int = Field(default=1800)

    # Job Scheduler Configuration
    job_scheduler_enabled: bool = Field(default=False)
    job_interval_seconds: int = Field(default=120)
    job_timeout_seconds: int = Field(default=600)  # 10 minutes for job execution
    max_tracked_players: int = Field(default=10)

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


async def get_setting_from_db(key: str) -> Optional[str]:
    """
    Get a setting value from the database.

    This function checks the database for runtime configuration overrides.
    Falls back to environment variables if not found in database.

    Always queries the database to ensure fresh values (no caching).
    Database queries are fast enough that caching adds unnecessary complexity.

    Note: This creates a new database engine/session. For use in contexts where
    no session exists (e.g., API endpoints). For jobs, prefer passing the session
    directly to get_riot_api_key(db) instead.
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    engine = None

    try:
        # Import here to avoid circular dependency
        from .models.settings import SystemSetting

        # Get database URL from environment
        settings = get_global_settings()
        engine = create_async_engine(settings.database_url, echo=False)
        async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

        async with async_session_maker() as session:
            stmt = select(SystemSetting).where(SystemSetting.key == key)
            result = await session.execute(stmt)
            setting = result.scalar_one_or_none()

            if setting:
                return setting.value

        return None

    except Exception:
        # If anything fails (table doesn't exist, etc.), return None
        # This allows the app to work even if database isn't set up yet
        return None
    finally:
        # Always dispose of the engine to prevent connection leaks
        if engine is not None:
            await engine.dispose()


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
            from .models.settings import SystemSetting

            stmt = select(SystemSetting).where(SystemSetting.key == "riot_api_key")
            result = await db.execute(stmt)
            setting = result.scalar_one_or_none()

            if setting:
                return setting.value
        except Exception:  # nosec B110
            # If database query fails, fall back to environment variable
            # Intentionally catching all exceptions to ensure graceful degradation
            pass

    settings = get_global_settings()
    return settings.riot_api_key
