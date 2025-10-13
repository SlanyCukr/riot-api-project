"""Configuration settings for the Riot API application."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from typing import List

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
