"""Pydantic schemas for Job models."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.models.job_tracking import JobType


class JobConfigurationBase(BaseModel):
    """Base job configuration schema with common fields."""

    job_type: JobType = Field(..., description="Type of job")
    name: str = Field(
        ..., min_length=1, max_length=128, description="Unique name for this job"
    )
    schedule: str = Field(
        ..., min_length=1, max_length=256, description="Job schedule (cron or interval)"
    )
    is_active: bool = Field(default=True, description="Whether the job is active")
    config_json: Optional[Dict[str, Any]] = Field(
        None, description="Job-specific configuration"
    )


class JobConfigurationCreate(JobConfigurationBase):
    """Schema for creating a new job configuration."""

    pass


class JobConfigurationUpdate(BaseModel):
    """Schema for updating an existing job configuration."""

    name: Optional[str] = Field(None, min_length=1, max_length=128)
    schedule: Optional[str] = Field(None, min_length=1, max_length=256)
    is_active: Optional[bool] = None
    config_json: Optional[Dict[str, Any]] = None
