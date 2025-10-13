"""Base job class for automated background jobs."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import JobConfiguration, JobExecution, JobStatus

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
        self.metrics = {
            "api_requests_made": 0,
            "records_created": 0,
            "records_updated": 0,
        }
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
            )
            db.add(self.job_execution)
            await db.commit()
            await db.refresh(self.job_execution)

            logger.info(
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
            self.job_execution.completed_at = datetime.now(timezone.utc)
            self.job_execution.status = (
                JobStatus.SUCCESS if success else JobStatus.FAILED
            )
            self.job_execution.api_requests_made = self.metrics["api_requests_made"]
            self.job_execution.records_created = self.metrics["records_created"]
            self.job_execution.records_updated = self.metrics["records_updated"]
            self.job_execution.error_message = error_message
            self.job_execution.execution_log = self.execution_log

            await db.commit()

            duration = (
                self.job_execution.completed_at - self.job_execution.started_at
            ).total_seconds()

            logger.info(
                "Job execution completed",
                job_type=self.job_config.job_type.value,
                job_name=self.job_config.name,
                execution_id=self.job_execution.id,
                status=self.job_execution.status.value,
                duration_seconds=duration,
                api_requests=self.metrics["api_requests_made"],
                records_created=self.metrics["records_created"],
                records_updated=self.metrics["records_updated"],
                success=success,
            )

        except Exception as e:
            logger.error(
                "Failed to log job completion",
                job_name=self.job_config.name,
                error=str(e),
                error_type=type(e).__name__,
            )
            await db.rollback()

    async def handle_error(self, db: AsyncSession, error: Exception) -> None:
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

        await self.log_completion(db, success=False, error_message=error_message)

    async def run(self) -> None:
        """Main entry point for job execution.

        This method:
        1. Creates database session
        2. Logs job start
        3. Executes job logic
        4. Logs completion (success or failure)
        5. Handles errors gracefully

        This method ensures that job execution is ALWAYS marked as complete
        (either success or failed) to prevent jobs from being stuck in RUNNING state.
        """
        db = None
        try:
            # Get database session
            async for db in get_db():
                try:
                    # Log job start
                    await self.log_start(db)

                    # Execute job logic
                    await self.execute(db)

                    # Log successful completion
                    await self.log_completion(db, success=True)

                except Exception as e:
                    # Handle and log error - this ensures log_completion is called
                    await self.handle_error(db, e)
                    # Don't re-raise here - we want to log the error but not crash the scheduler
                    logger.error(
                        "Job execution failed but was handled gracefully",
                        job_name=self.job_config.name,
                        error=str(e),
                        error_type=type(e).__name__,
                    )

                finally:
                    # Ensure database session is closed
                    if db:
                        await db.close()
                    break

        except Exception as e:
            logger.error(
                "Critical error in job execution wrapper",
                job_name=self.job_config.name,
                error=str(e),
                error_type=type(e).__name__,
            )
            # If we have a job_execution record but it's still RUNNING, mark it as failed
            if self.job_execution and self.job_execution.status == JobStatus.RUNNING:
                logger.warning(
                    "Job execution record exists but status is RUNNING after critical error, attempting to mark as failed",
                    job_name=self.job_config.name,
                    execution_id=self.job_execution.id,
                )
                # Try one more time to log completion if we have a db session
                if db:
                    try:
                        await self.log_completion(
                            db, success=False, error_message=f"Critical error: {str(e)}"
                        )
                    except Exception as cleanup_error:
                        logger.error(
                            "Failed to mark job as failed during cleanup",
                            job_name=self.job_config.name,
                            error=str(cleanup_error),
                        )

    def increment_metric(self, metric_name: str, count: int = 1) -> None:
        """Increment a metric counter.

        Args:
            metric_name: Name of the metric to increment.
            count: Amount to increment by (default: 1).
        """
        if metric_name in self.metrics:
            self.metrics[metric_name] += count
        else:
            logger.warning(
                "Unknown metric name",
                metric_name=metric_name,
                job_name=self.job_config.name,
            )

    def add_log_entry(self, key: str, value: Any) -> None:
        """Add an entry to the execution log.

        Args:
            key: Log entry key.
            value: Log entry value.
        """
        self.execution_log[key] = value
