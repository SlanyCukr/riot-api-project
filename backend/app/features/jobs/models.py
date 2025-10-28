"""Job tracking models for monitoring automated job execution.

SQLModel implementation following the pattern:
- Base models: Shared fields between database and API
- Table models: Database tables with table=True
- API models: Request/response schemas (if needed)
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime as SQLDateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel
from pydantic import ConfigDict


class JobType(str, PyEnum):
    """Enumeration of job types."""

    TRACKED_PLAYER_UPDATER = "TRACKED_PLAYER_UPDATER"
    MATCH_FETCHER = "MATCH_FETCHER"
    PLAYER_ANALYZER = "PLAYER_ANALYZER"
    BAN_CHECKER = "BAN_CHECKER"


class JobStatus(str, PyEnum):
    """Enumeration of job execution statuses."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RATE_LIMITED = "RATE_LIMITED"


# ============================================================================
# BASE MODELS - Shared fields between table and API
# ============================================================================


class JobConfigurationBase(SQLModel):
    """Base job configuration schema with shared fields."""

    # Job identification
    name: str = Field(
        max_length=128,
        unique=True,
        index=True,
        description="Unique name for this job configuration",
    )

    # Scheduling configuration
    schedule: str = Field(
        max_length=256,
        description="Job schedule (cron expression or interval specification)",
    )

    # Status and configuration
    is_active: bool = Field(
        default=True,
        index=True,
        description="Whether this job is active and should be scheduled",
    )


class JobExecutionBase(SQLModel):
    """Base job execution schema with shared fields."""

    # Execution metrics
    api_requests_made: int = Field(
        default=0,
        description="Number of API requests made during this execution",
    )

    records_created: int = Field(
        default=0,
        description="Number of database records created during this execution",
    )

    records_updated: int = Field(
        default=0,
        description="Number of database records updated during this execution",
    )


# ============================================================================
# TABLE MODELS - Database tables
# ============================================================================


class JobConfiguration(JobConfigurationBase, table=True):
    """Job configuration model storing job scheduling and settings."""

    __tablename__ = "job_configurations"
    __table_args__ = (
        Index("idx_job_config_type_active", "job_type", "is_active"),
        {"schema": "jobs"},
    )

    # Primary key
    id: Optional[int] = Field(
        default=None,
        primary_key=True,
        description="Auto-incrementing primary key",
    )

    # Job type - using sa_column for PostgreSQL ENUM
    job_type: JobType = Field(
        sa_column=Column(
            ENUM(JobType, name="job_type_enum", create_type=False, schema="jobs"),
            nullable=False,
            index=True,
        ),
        description="Type of job (tracked_player_updater, player_analyzer)",
    )

    # Job-specific configuration parameters
    config_json: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Job-specific configuration parameters in JSON format",
    )

    # Timestamps - server defaults
    created_at: datetime = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
        description="When this job configuration was created",
    )

    updated_at: datetime = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
        description="When this job configuration was last updated",
    )

    # Relationships
    executions: list["JobExecution"] = Relationship(
        back_populates="job_config",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "JobExecution.started_at.desc()",
        },
    )

    model_config = ConfigDict(from_attributes=True)

    def __repr__(self) -> str:
        """Return string representation of the job configuration."""
        return f"<JobConfiguration(id={self.id}, name='{self.name}', type='{self.job_type.value}', active={self.is_active})>"


class JobExecution(JobExecutionBase, table=True):
    """Job execution model storing job run history and metrics."""

    __tablename__ = "job_executions"
    __table_args__ = (
        Index("idx_job_execution_config_started", "job_config_id", "started_at"),
        Index("idx_job_execution_status_started", "status", "started_at"),
        {"schema": "jobs"},
    )

    # Primary key
    id: Optional[int] = Field(
        default=None,
        primary_key=True,
        description="Auto-incrementing primary key",
    )

    # Foreign key to job configuration
    job_config_id: int = Field(
        sa_column=Column(
            ForeignKey("jobs.job_configurations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        description="Reference to the job configuration",
    )

    # Execution status - using sa_column for PostgreSQL ENUM
    status: JobStatus = Field(
        default=JobStatus.PENDING,
        sa_column=Column(
            ENUM(JobStatus, name="job_status_enum", create_type=False, schema="jobs"),
            nullable=False,
            index=True,
        ),
        description="Current status of job execution",
    )

    # Execution timing
    started_at: datetime = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            index=True,
        ),
        description="When this job execution started",
    )

    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=True,
            index=True,
        ),
        description="When this job execution completed",
    )

    # Error handling
    error_message: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Error message if job execution failed",
    )

    # Detailed execution log
    execution_log: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Detailed execution log and metrics in JSON format",
    )

    # Detailed logs captured during execution
    detailed_logs: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="All logs captured during job execution (INFO, WARNING, ERROR, etc.)",
    )

    # Relationships
    job_config: JobConfiguration = Relationship(back_populates="executions")

    model_config = ConfigDict(from_attributes=True)

    def __repr__(self) -> str:
        """Return string representation of the job execution."""
        return f"<JobExecution(id={self.id}, config_id={self.job_config_id}, status='{self.status.value}', started={self.started_at})>"


# Note: Composite indexes are now defined in __table_args__ within each model class
# This follows SQLModel best practices for index management
