"""User model for authentication and authorization."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime as SQLDateTime,
    String,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.models import Base


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    # Primary key
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Auto-incrementing primary key",
    )

    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="User email address (unique)",
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Hashed password using Argon2id",
    )

    # Profile information
    display_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Display name shown in UI",
    )

    # Account status flags
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether the account is active (not disabled)",
    )

    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether the user has admin privileges",
    )

    # Email verification
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the email has been verified",
    )

    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=True,
        comment="When the email was verified",
    )

    # Activity tracking
    last_login: Mapped[Optional[datetime]] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When the user last logged in",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this user account was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When this user account was last updated",
    )

    def __repr__(self) -> str:
        """Return string representation of the user."""
        return f"<User(id={self.id}, email='{self.email}', display_name='{self.display_name}', is_admin={self.is_admin})>"


# Create composite indexes for common queries
Index("idx_users_is_active_is_admin", User.is_active, User.is_admin)
Index("idx_users_email_is_active", User.email, User.is_active)
Index("idx_users_last_login", User.last_login)
Index("idx_users_created_at", User.created_at)
