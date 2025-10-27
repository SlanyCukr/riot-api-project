"""
SQLModel models for authentication feature.

Replaces both models.py (SQLAlchemy) and schemas.py (Pydantic)
with unified SQLModel classes following conservative migration approach.

Pattern: Base → Table → API schemas
"""

from datetime import datetime
from typing import Optional
import re
from sqlmodel import SQLModel, Field
from pydantic import EmailStr, field_validator, ConfigDict


# ============================================================================
# BASE MODELS - Shared fields between table and API
# ============================================================================


class UserBase(SQLModel):
    """
    Shared user fields between database and API.

    Include only fields that appear in BOTH:
    - Database table (User)
    - API requests/responses (UserCreate, UserPublic)
    """

    email: EmailStr = Field(
        max_length=255, index=True, description="User's email address (unique)"
    )
    display_name: str = Field(max_length=128, description="Display name shown in UI")


# ============================================================================
# TABLE MODELS - Database tables (exact schema preservation)
# ============================================================================


class User(UserBase, table=True):
    """
    User database table.

    Maintains exact same schema as current auth.users table.
    Combines shared fields from UserBase with database-only fields.
    """

    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    # Primary key
    id: int = Field(primary_key=True, description="Auto-incrementing primary key")

    # Authentication fields (NEVER in API responses)
    password_hash: str = Field(
        description="Hashed password using Argon2id",
        exclude=True,  # Automatically excluded from API responses
    )

    # Account status flags
    is_active: bool = Field(
        default=True, index=True, description="Whether account is active (not disabled)"
    )
    is_admin: bool = Field(
        default=False, index=True, description="Whether user has admin privileges"
    )

    # Email verification
    email_verified: bool = Field(
        default=False, description="Whether email has been verified"
    )
    email_verified_at: Optional[datetime] = Field(
        default=None, description="When email was verified"
    )

    # Activity tracking
    last_login: Optional[datetime] = Field(
        default=None, index=True, description="When user last logged in"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this user account was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow},
        description="When this user account was last updated",
    )


# ============================================================================
# API MODELS - Request/response schemas
# ============================================================================


class UserCreate(UserBase):
    """
    Request to create a new user.

    Inherits email and display_name from UserBase.
    Adds password for registration only.
    """

    password: str = Field(
        min_length=8, max_length=128, description="Password (will be hashed)"
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Maintain existing password validation rules exactly."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        # Expanded special character set to support password managers
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_+=\[\]\\/;'`~]", v):
            raise ValueError(
                "Password must contain at least one special character "
                r"(!@#$%^&*(),.?\":{}|<>-_+=[]\/;'`~)"
            )

        return v


class UserLogin(SQLModel):
    """
    Request for user login.

    Separate from UserCreate as login doesn't need display_name.
    """

    email: EmailStr
    password: str


class UserPublic(UserBase):
    """
    User API response.

    Excludes sensitive data like password_hash.
    Includes read-only fields like timestamps.
    """

    id: int
    is_active: bool
    is_admin: bool
    email_verified: bool
    email_verified_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(SQLModel):
    """JWT token response (unchanged)."""

    access_token: str
    token_type: str = "bearer"


class TokenData(SQLModel):
    """Token payload data (unchanged)."""

    email: Optional[EmailStr] = None
    user_id: Optional[int] = None
