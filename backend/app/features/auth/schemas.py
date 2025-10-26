"""Pydantic schemas for authentication."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=128)


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets security requirements.

        Requirements:
        - At least 8 characters
        - At least one lowercase letter
        - At least one uppercase letter
        - At least one digit
        - At least one special character (expanded set to support password managers)

        Note: For more sophisticated strength checking (e.g., entropy-based validation),
        consider integrating zxcvbn library in the future. Current validation uses
        regex-based rules which are adequate for basic security requirements.
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        # Expanded special character set to support password managers
        # Includes common symbols: !@#$%^&*(),.?":{}|<>-_+=[]\/;'`~
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_+=\[\]\\/;'`~]", v):
            raise ValueError(
                "Password must contain at least one special character "
                r"(!@#$%^&*(),.?\":{}|<>-_+=[]\/;'`~)"
            )

        return v


class UserResponse(UserBase):
    """Schema for user responses (excludes sensitive data)."""

    id: int
    is_active: bool
    is_admin: bool
    email_verified: bool
    email_verified_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token payload data."""

    email: Optional[str] = None
    user_id: Optional[int] = None
