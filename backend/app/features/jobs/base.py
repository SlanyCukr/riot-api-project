"""Base job class for automated background jobs."""

from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import db_manager
from .models import JobConfiguration, JobExecution, JobStatus
from structlog import contextvars as structlog_contextvars
from .log_capture import job_log_capture
from .error_handling import RateLimitSignal

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

    def __init__(self, job_config_id: int):
        """Initialize the job with its configuration ID.

        Args:
            job_config_id: ID of job configuration from database.
        """
        self.job_config_id = job_config_id
        self.job_config: Optional[JobConfiguration] = None
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

    async def _refresh_config(self, db: AsyncSession) -> None:
        """Load fresh job configuration from database.

        Args:
            db: Database session for querying configuration.

        Raises:
            Exception: If configuration is missing or invalid.
        """
        stmt = select(JobConfiguration).where(JobConfiguration.id == self.job_config_id)
        result = await db.execute(stmt)
        job_config = result.scalar_one_or_none()

        if job_config is None:
            raise Exception(
                f"Job configuration {self.job_config_id} not found or deleted"
            )

        self.job_config = job_config
        logger.debug(
            "Job configuration refreshed",
            job_config_id=self.job_config_id,
            job_name=self.job_config.name,
            job_type=self.job_config.job_type.value,
        )

    async def log_start(self, db: AsyncSession) -> None:
        """Log job execution start and create JobExecution record."""
        try:
            self.job_execution = JobExecution(
                job_config_id=self.job_config_id,
                started_at=datetime.now(timezone.utc),
                status=JobStatus.RUNNING,
                api_requests_made=0,
                records_created=0,
                records_updated=0,
                execution_log={},
                detailed_logs=None,  # Will be populated on completion
            )
            db.add(self.job_execution)
            if not await self.safe_commit(db, "job start"):
                raise Exception("Failed to create job execution record")
            await db.refresh(self.job_execution)

            logger.debug(
                "Job execution started",
                job_config_id=self.job_config_id,
                execution_id=self.job_execution.id,
            )

        except Exception as e:
            logger.error(
                "Failed to log job start",
                job_config_id=self.job_config_id,
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
        status: Optional[JobStatus] = None,
    ) -> None:
        """Log job execution completion and update JobExecution record.

        :param db: Database session
        :param success: Whether the job succeeded
        :param error_message: Optional error message
        :param logs: Optional list of log entries
        :param status: Optional explicit status (overrides success-based status)
        """
        # Exit early if job execution was never started
        if self.job_execution is None:
            logger.warning(
                "Cannot log completion, job execution not started",
                job_config_id=self.job_config_id,
            )
            return

        try:
            completed_at = datetime.now(timezone.utc)
            duration = (completed_at - self.job_execution.started_at).total_seconds()

            self._log_completion_details(success, duration)

            # Prepare detailed logs for database storage
            detailed_logs = None
            if logs:
                detailed_logs = {"logs": self._strip_redundant_fields(logs)}

            update_stmt = self._build_completion_update_statement(
                JobExecution,
                completed_at,
                success,
                error_message,
                detailed_logs,
                status,
            )

            await self._execute_completion_update(db, update_stmt)

            # Update local execution object state
            self.job_execution.completed_at = completed_at
            # Use explicit status if provided, otherwise derive from success
            self.job_execution.status = (
                status
                if status is not None
                else (JobStatus.SUCCESS if success else JobStatus.FAILED)
            )

        except Exception as e:
            await self._handle_completion_error(db, e)

    async def is_already_running(self, db: AsyncSession) -> bool:
        """Check if this job is already running."""
        from sqlalchemy import select

        stmt = (
            select(JobExecution)
            .where(
                JobExecution.job_config_id == self.job_config_id,
                JobExecution.status == JobStatus.RUNNING,
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        running_job = result.scalar_one_or_none()

        if running_job:
            logger.info(
                "Job is already running, skipping execution",
                job_config_id=self.job_config_id,
                running_execution_id=running_job.id,
                running_since=running_job.started_at.isoformat()
                if running_job.started_at
                else None,
            )
            return True

        return False

    async def handle_error(self, db: AsyncSession, error: Exception) -> str:
        """Handle job execution error and return formatted error message."""
        error_message = f"{type(error).__name__}: {str(error)}"

        logger.error(
            "Job execution failed",
            job_config_id=self.job_config_id,
            job_type=self.job_config.job_type.value if self.job_config else None,
            job_name=self.job_config.name if self.job_config else None,
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
                    job_config_id=self.job_config_id,
                )
                return

            try:
                await self.log_start(db)
            except Exception as error:
                logger.error(
                    "Failed to initialize job execution",
                    job_config_id=self.job_config_id,
                    error=str(error),
                    error_type=type(error).__name__,
                )
                return

            try:
                # Load fresh configuration before execution
                await self._refresh_config(db)

                if self.job_execution:
                    structlog_contextvars.bind_contextvars(
                        job_execution_id=self.job_execution.id,
                        job_name=self.job_config.name,
                        job_type=self.job_config.job_type.value,
                    )

                await self.execute(db)

            except RateLimitSignal as rate_limit_signal:
                # Rate limit hit - save progress and mark as rate limited
                logger.warning(
                    "Job stopped due to rate limit",
                    job_config_id=self.job_config_id,
                    job_name=self.job_config.name,
                    retry_after=rate_limit_signal.retry_after,
                )
                job_logs = self._get_job_logs()
                await self.log_completion(
                    db,
                    success=True,  # Not a failure - completed what we could
                    logs=job_logs,
                    status=JobStatus.RATE_LIMITED,
                )
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

    async def safe_commit(
        self,
        db: AsyncSession,
        operation: str = "database operation",
        on_success: Optional[Callable[[], None]] = None,
    ) -> bool:
        """Safely commit database changes with automatic rollback on failure.

        Executes optional callback only after successful commit.
        Returns True on success, False on failure (logs error automatically).
        """
        try:
            await db.commit()
            if on_success:
                on_success()
            return True
        except Exception as e:
            await db.rollback()
            logger.error(
                f"Failed to commit {operation}",
                error=str(e),
                error_type=type(e).__name__,
                job_config_id=self.job_config_id,
                execution_id=self.job_execution.id if self.job_execution else None,
            )
            return False

    def _get_job_logs(self) -> List[Dict[str, Any]]:
        """Extract logs for this job execution."""
        if self.job_execution is None:
            return []

        return [
            entry
            for entry in job_log_capture.entries
            if entry.get("job_execution_id") == self.job_execution.id
        ]

    def _strip_redundant_fields(
        self, logs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove fields that are redundant in DB (already in job_execution table).

        Keep them in stdout for debugging, strip only before DB storage.
        Note: 'level' is NOT stripped because each log entry can have a different level.
        """
        redundant_fields = {
            "job_execution_id",
            "job_name",
            "job_type",
            "logger",
        }

        return [
            {k: v for k, v in entry.items() if k not in redundant_fields}
            for entry in logs
        ]

    def increment_metric(self, metric_name: str, count: int = 1) -> None:
        """Increment a metric counter."""
        self.metrics[metric_name] += count

    def add_log_entry(self, key: str, value: Any) -> None:
        """Add an entry to the execution log."""
        self.execution_log[key] = value

    # Private helper methods

    def _log_completion_details(self, success: bool, duration: float) -> None:
        """Log completion details to structured logger."""
        logger.debug(
            "Job execution completed",
            job_config_id=self.job_config_id,
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

    def _build_completion_update_statement(
        self,
        job_execution_model,
        completed_at,
        success,
        error_message,
        detailed_logs,
        status=None,
    ):
        """Build SQLAlchemy update statement for job completion."""
        from sqlalchemy import update

        # Use explicit status if provided, otherwise derive from success
        final_status = (
            status
            if status is not None
            else (JobStatus.SUCCESS if success else JobStatus.FAILED)
        )

        return (
            update(job_execution_model)
            .where(job_execution_model.id == self.job_execution.id)
            .values(
                completed_at=completed_at,
                status=final_status,
                api_requests_made=self.metrics["api_requests_made"],
                records_created=self.metrics["records_created"],
                records_updated=self.metrics["records_updated"],
                error_message=error_message,
                execution_log=self.execution_log,
                detailed_logs=detailed_logs,
            )
        )

    async def _execute_completion_update(self, db: AsyncSession, stmt) -> None:
        """Execute the completion update with retry logic."""
        try:
            await db.execute(stmt)
            if await self.safe_commit(db, "job completion"):
                return
        except Exception as execute_error:
            logger.error(
                "Failed to execute job completion update",
                job_config_id=self.job_config_id,
                execution_id=self.job_execution.id,
                error=str(execute_error),
                error_type=type(execute_error).__name__,
            )

        # Retry once after rollback
        try:
            await db.rollback()
            await db.execute(stmt)
            if await self.safe_commit(db, "job completion retry"):
                logger.info(
                    "Successfully committed job completion on retry",
                    execution_id=self.job_execution.id,
                )
            else:
                logger.warning(
                    "Job completion retry commit failed - job may remain stuck",
                    execution_id=self.job_execution.id,
                )
        except Exception as retry_error:
            logger.error(
                "Failed to execute job completion retry - job may remain stuck",
                job_config_id=self.job_config_id,
                execution_id=self.job_execution.id,
                error=str(retry_error),
                error_type=type(retry_error).__name__,
            )
            # Don't raise - we want the job to complete even if logging fails

    async def _handle_completion_error(
        self, db: AsyncSession, error: Exception
    ) -> None:
        """Handle errors that occur during completion logging."""
        logger.error(
            "Failed to log job completion",
            job_config_id=self.job_config_id,
            execution_id=self.job_execution.id if self.job_execution else None,
            error=str(error),
            error_type=type(error).__name__,
            exc_info=True,
        )
        try:
            await db.rollback()
        except Exception as rollback_error:
            logger.error(
                "Failed to rollback after log_completion error",
                error=str(rollback_error),
            )
