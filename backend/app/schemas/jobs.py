"""Pydantic schemas for Job models."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict

from app.models.job_tracking import JobStatus, JobType


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


class JobConfigurationResponse(JobConfigurationBase):
    """Schema for job configuration response data."""

    id: int = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class JobExecutionResponse(BaseModel):
    """Schema for job execution response data."""

    id: int = Field(..., description="Unique identifier")
    job_config_id: int = Field(..., description="Reference to job configuration")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: Optional[datetime] = Field(
        None, description="Execution completion time"
    )
    status: JobStatus = Field(..., description="Execution status")
    api_requests_made: int = Field(default=0, description="Number of API requests made")
    records_created: int = Field(default=0, description="Number of records created")
    records_updated: int = Field(default=0, description="Number of records updated")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    execution_log: Optional[Dict[str, Any]] = Field(
        None, description="Detailed execution log"
    )
    detailed_logs: Optional[Dict[str, Any]] = Field(
        None,
        description="All logs captured during execution (includes logs array and summary)",
    )

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    """Schema for overall job system status."""

    scheduler_running: bool = Field(..., description="Whether the scheduler is running")
    active_jobs: int = Field(..., description="Number of active job configurations")
    running_executions: int = Field(
        ..., description="Number of currently running executions"
    )
    last_execution: Optional[JobExecutionResponse] = Field(
        None, description="Most recent job execution"
    )
    next_run_time: Optional[datetime] = Field(
        None, description="When the next job is scheduled"
    )


class JobTriggerResponse(BaseModel):
    """Schema for manual job trigger response."""

    success: bool = Field(..., description="Whether the job was triggered successfully")
    message: str = Field(..., description="Result message")
    execution_id: Optional[int] = Field(
        None, description="ID of created execution record"
    )


class JobExecutionListResponse(BaseModel):
    """Schema for paginated job execution list response."""

    executions: list[JobExecutionResponse]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)
