"""System settings model for storing runtime configuration."""

from datetime import datetime

from sqlalchemy import Column, DateTime as SQLDateTime, Text
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class SystemSettingBase(SQLModel):
    """Base system setting schema with shared fields."""

    value: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Setting value",
    )
    category: str = Field(
        max_length=64,
        description="Setting category (e.g., 'riot_api', 'jobs', 'app')",
    )
    is_sensitive: bool = Field(
        default=False,
        description="Whether this setting contains sensitive data (should be masked)",
    )


class SystemSetting(SystemSettingBase, table=True):
    """System settings model for runtime configuration."""

    __tablename__ = "system_settings"
    __table_args__ = {"schema": "jobs"}

    # Primary key
    key: str = Field(
        primary_key=True,
        max_length=128,
        index=True,
        description="Setting key (e.g., 'riot_api_key')",
    )

    # Timestamps - let PostgreSQL handle defaults
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
        description="When this setting was created",
    )

    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
        description="When this setting was last updated",
    )

    def __repr__(self) -> str:
        """Return string representation of the setting."""
        # Always mask values in __repr__ to prevent accidental exposure in logs
        value_display = "***"
        return f"<SystemSetting(key='{self.key}', category='{self.category}', value='{value_display}')>"

    def mask_value(self) -> str:
        """Return masked value for sensitive settings."""
        if not self.is_sensitive:
            return self.value

        # Show only last 4 characters
        if len(self.value) <= 4:
            return "****"
        return f"****-****-{self.value[-4:]}"
