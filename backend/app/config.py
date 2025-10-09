"""Configuration settings for the Riot API application."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Riot API Configuration
    riot_api_key: str = Field(..., env="RIOT_API_KEY")
    riot_region: str = Field(default="europe", env="RIOT_REGION")
    riot_platform: str = Field(default="eun1", env="RIOT_PLATFORM")

    # Database Configuration
    postgres_db: str = Field(default="riot_api_db", env="POSTGRES_DB")
    postgres_user: str = Field(default="riot_api_user", env="POSTGRES_USER")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")
    database_url: str = Field(..., env="DATABASE_URL")

    # Application Configuration
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Frontend Configuration
    api_url: str = Field(default="http://localhost:8000", env="API_URL")

    # CORS Configuration
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000", env="CORS_ORIGINS"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    # Database Connection Pool Settings
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=1800, env="DB_POOL_RECYCLE")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


# Create a global settings instance
settings = get_settings()
