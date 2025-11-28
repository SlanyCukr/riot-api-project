"""Job tracking models for monitoring automated job execution."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    DateTime as SQLDateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.models import Base


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


class JobConfiguration(Base):
    """Job configuration model storing job scheduling and settings."""

    __tablename__ = "job_configurations"
    __table_args__ = {"schema": "jobs"}

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier for job configuration",
    )

    # Job identification
    job_type: Mapped[JobType] = mapped_column(
        ENUM(JobType, name="job_type_enum", create_type=False, schema="jobs"),
        nullable=False,
        index=True,
        comment="Type of job (tracked_player_updater, player_analyzer)",
    )

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique name for this job configuration",
    )

    # Scheduling configuration
    schedule: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment="Job schedule (cron expression or interval specification)",
    )

    # Status and configuration
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this job is active and should be scheduled",
    )

    config_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Job-specific configuration parameters in JSON format",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this job configuration was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When this job configuration was last updated",
    )

    # Relationships
    executions = relationship(
        "JobExecution",
        back_populates="job_config",
        cascade="all, delete-orphan",
        order_by="JobExecution.started_at.desc()",
    )

    def __repr__(self) -> str:
        """Return string representation of the job configuration."""
        return f"<JobConfiguration(id={self.id}, name='{self.name}', type='{self.job_type.value}', active={self.is_active})>"


class JobExecution(Base):
    """Job execution model storing job run history and metrics."""

    __tablename__ = "job_executions"
    __table_args__ = {"schema": "jobs"}

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier for job execution",
    )

    # Foreign key to job configuration
    job_config_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("jobs.job_configurations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the job configuration",
    )

    # Execution timing
    started_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="When this job execution started",
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When this job execution completed",
    )

    # Execution status
    status: Mapped[JobStatus] = mapped_column(
        ENUM(JobStatus, name="job_status_enum", create_type=False, schema="jobs"),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
        comment="Current status of job execution",
    )

    # Execution metrics
    api_requests_made: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of API requests made during this execution",
    )

    records_created: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of database records created during this execution",
    )

    records_updated: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of database records updated during this execution",
    )

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if job execution failed",
    )

    # Detailed execution log
    execution_log: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Detailed execution log and metrics in JSON format",
    )

    # Detailed logs captured during execution
    detailed_logs: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="All logs captured during job execution (INFO, WARNING, ERROR, etc.)",
    )

    # Relationships
    job_config = relationship("JobConfiguration", back_populates="executions")

    def __repr__(self) -> str:
        """Return string representation of the job execution."""
        return f"<JobExecution(id={self.id}, config_id={self.job_config_id}, status='{self.status.value}', started={self.started_at})>"


# Create composite indexes for common queries
Index(
    "idx_job_config_type_active",
    JobConfiguration.job_type,
    JobConfiguration.is_active,
)

Index(
    "idx_job_execution_config_started",
    JobExecution.job_config_id,
    JobExecution.started_at.desc(),
)

Index(
    "idx_job_execution_status_started",
    JobExecution.status,
    JobExecution.started_at.desc(),
)
