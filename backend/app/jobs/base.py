"""Base job class for automated background jobs."""

from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import db_manager
from app.models import JobConfiguration, JobExecution, JobStatus
from structlog import contextvars as structlog_contextvars
from .log_capture import job_log_capture

logger = structlog.get_logger(__name__)


class BaseJob(ABC):
    """Abstract base class for all automated jobs.

    Provides common functionality for job execution:
    - Job execution tracking and logging
    - Error handling and metrics collection
    - Database session management
    - Structured logging with correlation IDs

    Subclasses must implement:
    - execute(): The main job logic
    """

    def __init__(self, job_config: JobConfiguration):
        """Initialize the job with its configuration.

        Args:
            job_config: Job configuration from database.
        """
        self.job_config = job_config
        self.job_execution: Optional[JobExecution] = None
        self.metrics = defaultdict(int)
        self.metrics.update(
            {
                "api_requests_made": 0,
                "records_created": 0,
                "records_updated": 0,
            }
        )
        self.execution_log: Dict[str, Any] = {}

    @abstractmethod
    async def execute(self, db: AsyncSession) -> None:
        """Execute the job logic.

        This method must be implemented by subclasses.
        It should contain the main job logic and use self.metrics
        to track execution statistics.

        Args:
            db: Database session for job execution.

        Raises:
            Exception: If job execution fails.
        """
        pass

    async def log_start(self, db: AsyncSession) -> None:
        """Log job execution start and create JobExecution record.

        Args:
            db: Database session for creating execution record.
        """
        try:
            self.job_execution = JobExecution(
                job_config_id=self.job_config.id,
                started_at=datetime.now(timezone.utc),
                status=JobStatus.RUNNING,
                api_requests_made=0,
                records_created=0,
                records_updated=0,
                execution_log={},
                detailed_logs=None,  # Will be populated on completion
            )
            db.add(self.job_execution)
            await db.commit()
            await db.refresh(self.job_execution)

            logger.debug(
                "Job execution started",
                job_type=self.job_config.job_type.value,
                job_name=self.job_config.name,
                execution_id=self.job_execution.id,
            )

        except Exception as e:
            logger.error(
                "Failed to log job start",
                job_name=self.job_config.name,
                error=str(e),
                error_type=type(e).__name__,
            )
            await db.rollback()
            raise

    async def log_completion(
        self,
        db: AsyncSession,
        success: bool = True,
        error_message: Optional[str] = None,
        logs: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Log job execution completion and update JobExecution record.

        Args:
            db: Database session for updating execution record.
            success: Whether job completed successfully.
            error_message: Error message if job failed.
        """
        if self.job_execution is None:
            logger.warning(
                "Cannot log completion, job execution not started",
                job_name=self.job_config.name,
            )
            return

        try:
            # Get a fresh copy of the job execution from the database
            # This ensures we're working with an attached object in the current session
            from sqlalchemy import update
            from ..models.job_tracking import JobExecution

            completed_at = datetime.now(timezone.utc)
            duration = (completed_at - self.job_execution.started_at).total_seconds()

            logger.debug(
                "Job execution completed",
                job_type=self.job_config.job_type.value,
                job_name=self.job_config.name,
                execution_id=self.job_execution.id,
                status=JobStatus.SUCCESS.value if success else JobStatus.FAILED.value,
                duration_seconds=duration,
                api_requests=self.metrics["api_requests_made"],
                records_created=self.metrics["records_created"],
                records_updated=self.metrics["records_updated"],
                success=success,
            )

            # Strip redundant fields before DB storage (keep in stdout for debugging)
            detailed_logs = (
                {"logs": self._strip_redundant_fields(logs)} if logs else None
            )

            # Use an UPDATE statement instead of ORM to avoid session state issues
            stmt = (
                update(JobExecution)
                .where(JobExecution.id == self.job_execution.id)
                .values(
                    completed_at=completed_at,
                    status=JobStatus.SUCCESS if success else JobStatus.FAILED,
                    api_requests_made=self.metrics["api_requests_made"],
                    records_created=self.metrics["records_created"],
                    records_updated=self.metrics["records_updated"],
                    error_message=error_message,
                    execution_log=self.execution_log,
                    detailed_logs=detailed_logs,
                )
            )

            try:
                await db.execute(stmt)
                await db.commit()
            except Exception as commit_error:
                logger.error(
                    "Failed to commit job completion - attempting rollback and retry",
                    job_name=self.job_config.name,
                    execution_id=self.job_execution.id,
                    error=str(commit_error),
                    error_type=type(commit_error).__name__,
                )
                try:
                    await db.rollback()
                    # Try one more time with a fresh transaction
                    await db.execute(stmt)
                    await db.commit()
                    logger.info(
                        "Successfully committed job completion on retry",
                        execution_id=self.job_execution.id,
                    )
                except Exception as retry_error:
                    logger.error(
                        "Failed to commit job completion even after retry - job may remain stuck",
                        job_name=self.job_config.name,
                        execution_id=self.job_execution.id,
                        error=str(retry_error),
                        error_type=type(retry_error).__name__,
                    )
                    # Don't raise - we want the job to complete even if logging fails
                    return

            # Update local object for logging purposes
            self.job_execution.completed_at = completed_at
            self.job_execution.status = (
                JobStatus.SUCCESS if success else JobStatus.FAILED
            )

        except Exception as e:
            logger.error(
                "Failed to log job completion",
                job_name=self.job_config.name,
                execution_id=self.job_execution.id if self.job_execution else None,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,  # Include full traceback
            )
            try:
                await db.rollback()
            except Exception as rollback_error:
                logger.error(
                    "Failed to rollback after log_completion error",
                    error=str(rollback_error),
                )

    async def is_already_running(self, db: AsyncSession) -> bool:
        """Check if this job is already running.

        Args:
            db: Database session for querying execution records.

        Returns:
            True if job is already running, False otherwise.
        """
        from sqlalchemy import select

        stmt = (
            select(JobExecution)
            .where(
                JobExecution.job_config_id == self.job_config.id,
                JobExecution.status == JobStatus.RUNNING,
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        running_job = result.scalar_one_or_none()

        if running_job:
            logger.info(
                "Job is already running, skipping execution",
                job_type=self.job_config.job_type.value,
                job_name=self.job_config.name,
                running_execution_id=running_job.id,
                running_since=running_job.started_at.isoformat()
                if running_job.started_at
                else None,
            )
            return True

        return False

    async def handle_error(self, db: AsyncSession, error: Exception) -> str:
        """Handle job execution error.

        Args:
            db: Database session for updating execution record.
            error: Exception that was raised during job execution.
        """
        error_message = f"{type(error).__name__}: {str(error)}"

        logger.error(
            "Job execution failed",
            job_type=self.job_config.job_type.value,
            job_name=self.job_config.name,
            execution_id=self.job_execution.id if self.job_execution else None,
            error=error_message,
            error_type=type(error).__name__,
        )
        return error_message

    @asynccontextmanager
    async def _db_session(self):
        async with db_manager.get_session() as session:
            yield session

    async def run(self) -> None:
        """Execute the job with proper error handling and logging."""
        async with self._db_session() as db:
            if await self.is_already_running(db):
                logger.info(
                    "Skipping job execution - already running",
                    job_type=self.job_config.job_type.value,
                    job_name=self.job_config.name,
                )
                return

            try:
                await self.log_start(db)
            except Exception as error:
                logger.error(
                    "Failed to initialize job execution",
                    job_name=self.job_config.name,
                    error=str(error),
                    error_type=type(error).__name__,
                )
                return

            try:
                if self.job_execution:
                    structlog_contextvars.bind_contextvars(
                        job_execution_id=self.job_execution.id,
                        job_name=self.job_config.name,
                        job_type=self.job_config.job_type.value,
                    )

                await self.execute(db)

            except Exception as job_error:
                error_message = await self.handle_error(db, job_error)
                job_logs = self._get_job_logs()
                await self.log_completion(
                    db,
                    success=False,
                    error_message=error_message,
                    logs=job_logs,
                )
            else:
                job_logs = self._get_job_logs()
                await self.log_completion(
                    db,
                    success=True,
                    logs=job_logs,
                )
            finally:
                structlog_contextvars.clear_contextvars()
                self._cleanup_log_buffer()

    def _get_job_logs(self) -> List[Dict[str, Any]]:
        """Extract logs for this job execution."""
        if self.job_execution is None:
            return []

        return [
            entry
            for entry in job_log_capture.entries
            if entry.get("job_execution_id") == self.job_execution.id
        ]

    def _cleanup_log_buffer(self) -> None:
        """Prevent memory buildup."""
        if len(job_log_capture.entries) > 10000:
            job_log_capture.entries.clear()

    def _strip_redundant_fields(
        self, logs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove fields that are redundant in DB (already in job_execution table).

        Keep them in stdout for debugging, strip only before DB storage.
        """
        redundant_fields = {
            "job_execution_id",
            "job_name",
            "job_type",
            "logger",
            "level",
        }

        return [
            {k: v for k, v in entry.items() if k not in redundant_fields}
            for entry in logs
        ]

    def increment_metric(self, metric_name: str, count: int = 1) -> None:
        """Increment a metric counter."""
        self.metrics[metric_name] += count

    def add_log_entry(self, key: str, value: Any) -> None:
        """Add an entry to the execution log.

        Args:
            key: Log entry key.
            value: Log entry value.
        """
        self.execution_log[key] = value
