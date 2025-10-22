"""Scheduler module for managing automated background jobs."""

from typing import Dict, Optional, Type
from datetime import datetime

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_global_settings
from app.core import db_manager
from app.models import JobExecution, JobStatus, JobConfiguration, JobType
from .base import BaseJob

logger = structlog.get_logger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None
_JOB_REGISTRY: Optional[Dict[JobType, Type[BaseJob]]] = None


def _get_job_registry() -> Dict[JobType, Type[BaseJob]]:
    global _JOB_REGISTRY
    if _JOB_REGISTRY is None:
        from .tracked_player_updater import TrackedPlayerUpdaterJob
        from .match_fetcher import MatchFetcherJob
        from .smurf_analyzer import SmurfAnalyzerJob
        from .ban_checker import BanCheckerJob

        _JOB_REGISTRY = {
            JobType.TRACKED_PLAYER_UPDATER: TrackedPlayerUpdaterJob,
            JobType.MATCH_FETCHER: MatchFetcherJob,
            JobType.SMURF_ANALYZER: SmurfAnalyzerJob,
            JobType.BAN_CHECKER: BanCheckerJob,
        }

    return _JOB_REGISTRY


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """Get the global scheduler instance.

    Returns:
        The scheduler instance if initialized, None otherwise.
    """
    return _scheduler


def _resolve_interval_seconds(job_config: JobConfiguration) -> int:
    """Determine interval seconds for a job configuration.

    :param job_config: Job configuration with schedule settings.
    :returns: Interval in seconds (minimum 1).
    :raises ValueError: If no valid interval configuration found.
    """
    config = job_config.config_json or {}
    custom_value = config.get("interval_seconds")

    # Try to parse custom value from config
    interval_from_config = _parse_interval_from_config(custom_value)
    if interval_from_config:
        return interval_from_config

    # Try to parse from schedule string
    schedule = (job_config.schedule or "").strip().lower()
    interval_from_schedule = _parse_interval_from_schedule(schedule)
    if interval_from_schedule:
        return interval_from_schedule

    # No valid configuration found - fail hard
    raise ValueError(
        f"No valid interval configuration found for job '{job_config.name}'. "
        f"Either set 'interval_seconds' in config_json or provide a valid schedule string."
    )


def _parse_interval_from_config(custom_value: any) -> Optional[int]:
    """Parse interval from config JSON value.

    :param custom_value: Value from config_json['interval_seconds'].
    :returns: Parsed interval in seconds, or None if invalid.
    """
    # Exit early if no value provided
    if not custom_value:
        return None

    # Convert string digits to int
    if isinstance(custom_value, str) and custom_value.isdigit():
        custom_value = int(custom_value)

    # Return if valid positive integer
    if isinstance(custom_value, int) and custom_value > 0:
        return custom_value

    return None


def _parse_interval_from_schedule(schedule: str) -> Optional[int]:
    """Parse interval from schedule string.

    Supports formats:
    - "60" - plain number
    - "interval:60" - interval prefix
    - "60s" - seconds suffix

    :param schedule: Schedule string from job configuration.
    :returns: Parsed interval in seconds (minimum 1), or None if invalid.
    """
    # Exit early if empty
    if not schedule:
        return None

    # Try plain digit format: "60"
    if schedule.isdigit():
        return max(int(schedule), 1)

    # Try "interval:60" format
    if schedule.startswith("interval:"):
        candidate = schedule.split(":", 1)[1].strip()
        if candidate.isdigit():
            return max(int(candidate), 1)

    # Try "60s" format
    if schedule.endswith("s") and schedule[:-1].isdigit():
        return max(int(schedule[:-1]), 1)

    return None


async def _mark_stale_jobs_as_failed(db: AsyncSession) -> None:
    """Mark jobs that are stuck in 'running' state as failed on startup.

    This handles cases where jobs were running when the application was
    shut down ungracefully. On startup, we mark ALL running jobs as failed
    since no jobs should be running during application startup.

    Args:
        db: Database session for updating job records.
    """
    try:
        from sqlalchemy import select, update

        # Find ALL running jobs (none should exist during startup)
        stmt = select(JobExecution).where(JobExecution.status == JobStatus.RUNNING)
        result = await db.execute(stmt)
        stale_jobs = result.scalars().all()

        if stale_jobs:
            logger.warning(
                "Found jobs stuck in running state on startup",
                count=len(stale_jobs),
                job_ids=[job.id for job in stale_jobs],
            )

            # Update them to failed status
            update_stmt = (
                update(JobExecution)
                .where(JobExecution.status == JobStatus.RUNNING)
                .values(
                    status=JobStatus.FAILED,
                    completed_at=datetime.now(),
                    error_message="Job marked as failed - was still running during application startup (likely ungraceful shutdown or crash)",
                )
            )
            await db.execute(update_stmt)
            await db.commit()

            logger.info(
                "Marked stale jobs as failed",
                count=len(stale_jobs),
            )
        else:
            logger.info("No stale jobs found on startup")

    except Exception as e:
        logger.error(
            "Failed to mark stale jobs as failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        await db.rollback()


async def start_scheduler() -> AsyncIOScheduler:
    """Initialize and start the APScheduler instance.

    This function:
    1. Checks if scheduler should be enabled via configuration
    2. Creates scheduler with SQLAlchemy job store
    3. Marks stale running jobs as failed
    4. Starts the scheduler
    5. Loads job configurations from database and schedules them

    Returns:
        The initialized and started scheduler instance.

    Raises:
        Exception: If scheduler initialization fails.
    """
    global _scheduler

    settings = get_global_settings()

    if not settings.job_scheduler_enabled:
        logger.info("Job scheduler is disabled via configuration")
        return None

    if _scheduler is not None:
        logger.warning("Scheduler already initialized")
        return _scheduler

    try:
        logger.info("Initializing job scheduler")

        # Convert synchronous database URL to SQLAlchemy format for job store
        # APScheduler's SQLAlchemyJobStore uses synchronous connections
        jobstore_url = settings.database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://"
        )

        # Configure job stores (where APScheduler stores its internal state)
        jobstores = {
            "default": SQLAlchemyJobStore(url=jobstore_url),
        }

        # Configure executors (how jobs are executed)
        executors = {
            "default": AsyncIOExecutor(),  # Async executor for our async jobs
        }

        # Configure job defaults
        job_defaults = {
            "coalesce": True,  # Combine multiple missed runs into one
            "max_instances": 1,  # Only one instance of each job at a time
            "misfire_grace_time": 60,  # Allow 60 seconds grace for missed jobs
        }

        # Create scheduler
        _scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )

        # Mark stale jobs as failed before starting
        async with db_manager.get_session() as db:
            await _mark_stale_jobs_as_failed(db)

        # Start the scheduler
        _scheduler.start()

        logger.info(
            "Job scheduler started successfully",
        )

        # Load and schedule job configurations from database
        await _load_and_schedule_jobs()

        return _scheduler

    except Exception as e:
        logger.error(
            "Failed to start job scheduler",
            error=str(e),
            error_type=type(e).__name__,
        )
        _scheduler = None
        raise


def _convert_job_type(job_config: JobConfiguration) -> Optional[JobType]:
    """Convert job configuration type to JobType enum.

    :param job_config: Job configuration to convert.
    :returns: JobType enum, or None if invalid.
    """
    job_type = job_config.job_type
    if isinstance(job_type, str):
        try:
            return JobType(job_type)
        except ValueError:
            logger.warning(
                "Invalid job type, skipping",
                job_type=job_config.job_type,
                job_name=job_config.name,
            )
            return None
    return job_type


def _get_job_class(job_type: JobType, job_config: JobConfiguration, registry: Dict):
    """Get job class from registry.

    :param job_type: Type of job to get.
    :param job_config: Job configuration for logging.
    :param registry: Job registry mapping.
    :returns: Job class, or None if not found.
    """
    job_class = registry.get(job_type)
    if not job_class:
        logger.warning(
            "Unknown job type, skipping",
            job_type=job_type.value if isinstance(job_type, JobType) else str(job_type),
            job_name=job_config.name,
        )
    return job_class


def _schedule_job(
    job_config: JobConfiguration, job_class: Type[BaseJob], interval_seconds: int
):
    """Schedule a single job with the scheduler.

    :param job_config: Job configuration.
    :param job_class: Job class to instantiate.
    :param interval_seconds: Interval in seconds.
    """
    job_instance = job_class(job_config.id)
    job_type = job_config.job_type

    _scheduler.add_job(
        job_instance.run,
        trigger="interval",
        seconds=interval_seconds,
        id=f"job_{job_config.id}",
        name=job_config.name,
        replace_existing=True,
    )

    logger.info(
        "Scheduled job",
        job_id=job_config.id,
        job_name=job_config.name,
        job_type=job_type.value if isinstance(job_type, JobType) else str(job_type),
        interval_seconds=interval_seconds,
    )


async def _load_and_schedule_jobs() -> None:
    """Load job configurations from database and schedule them.

    This function queries active job configurations and schedules them
    with the appropriate job classes.
    """
    if _scheduler is None:
        logger.warning("Cannot load jobs, scheduler not initialized")
        return

    try:
        logger.info("Loading job configurations from database")
        from sqlalchemy import select

        async with db_manager.get_session() as db:
            stmt = select(JobConfiguration).where(JobConfiguration.is_active)
            result = await db.execute(stmt)
            job_configs = result.scalars().all()

        if not job_configs:
            logger.info("No active job configurations found")
            return

        registry = _get_job_registry()

        for job_config in job_configs:
            job_type = _convert_job_type(job_config)
            if not job_type:
                continue

            job_class = _get_job_class(job_type, job_config, registry)
            if not job_class:
                continue

            interval_seconds = _resolve_interval_seconds(job_config)
            _schedule_job(job_config, job_class, interval_seconds)

        logger.info("Successfully loaded and scheduled jobs", count=len(job_configs))

    except Exception as e:
        logger.error(
            "Failed to load and schedule jobs",
            error=str(e),
            error_type=type(e).__name__,
        )
        # Don't raise - scheduler can still run manually triggered jobs


async def shutdown_scheduler() -> None:
    """Gracefully shutdown the scheduler.

    This function:
    1. Waits for running jobs to complete
    2. Shuts down the scheduler
    3. Cleans up resources
    """
    global _scheduler

    if _scheduler is None:
        logger.info("Scheduler is not running, nothing to shutdown")
        return

    try:
        logger.info("Shutting down job scheduler")

        # Wait for running jobs to complete (with timeout)
        _scheduler.shutdown(wait=True)

        _scheduler = None

        logger.info("Job scheduler shut down successfully")

    except Exception as e:
        logger.error(
            "Error during scheduler shutdown",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
