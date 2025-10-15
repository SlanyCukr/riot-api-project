"""Pydantic schemas for system settings."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class SettingBase(BaseModel):
    """Base setting schema."""

    key: str = Field(..., description="Setting key")
    value: str = Field(..., description="Setting value")
    category: str = Field(..., description="Setting category")
    is_sensitive: bool = Field(False, description="Whether value should be masked")


class SettingCreate(SettingBase):
    """Schema for creating a new setting."""

    pass


class SettingUpdate(BaseModel):
    """Schema for updating a setting value."""

    value: str = Field(..., min_length=1, description="New setting value")


class SettingResponse(BaseModel):
    """Schema for setting response.

    Note: For security, only masked_value is populated for sensitive settings.
    The full value is never sent to the frontend.
    """

    key: str
    masked_value: str = Field(..., description="Masked value for sensitive settings")
    category: str
    is_sensitive: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SettingValidationResponse(BaseModel):
    """Schema for setting validation response."""

    valid: bool = Field(..., description="Whether the value is valid")
    message: str = Field(..., description="Validation message")
    details: Optional[str] = Field(None, description="Additional validation details")


class SettingTestResponse(BaseModel):
    """Schema for setting test response."""

    success: bool = Field(..., description="Whether the test was successful")
    message: str = Field(..., description="Test result message")
    details: Optional[dict] = Field(None, description="Additional test details")
