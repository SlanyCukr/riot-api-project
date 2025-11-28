"""System settings model for storing runtime configuration."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime as SQLDateTime,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.models import Base


class SystemSetting(Base):
    """System settings model for runtime configuration."""

    __tablename__ = "system_settings"
    __table_args__ = {"schema": "jobs"}

    # Primary key
    key: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
        index=True,
        comment="Setting key (e.g., 'riot_api_key')",
    )

    # Setting value
    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Setting value",
    )

    # Metadata
    category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Setting category (e.g., 'riot_api', 'jobs', 'app')",
    )

    is_sensitive: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this setting contains sensitive data (should be masked)",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this setting was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When this setting was last updated",
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
