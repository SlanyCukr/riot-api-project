"""Job management API endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from .models import JobStatus, JobType
from .schemas import (
    JobConfigurationUpdate,
    JobConfigurationResponse,
    JobExecutionListResponse,
    JobStatusResponse,
    JobTriggerResponse,
)
from .dependencies import JobServiceDep
from .implementations.tracked_player_updater import TrackedPlayerUpdaterJob
from .implementations.match_fetcher import MatchFetcherJob
from .implementations.player_analyzer import PlayerAnalyzerJob
from .implementations.ban_checker import BanCheckerJob
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _create_job_instance(job):
    """Create a job instance based on job type.

    Args:
        job: Job configuration (JobConfiguration or JobConfigurationResponse)

    Returns:
        Job instance based on job type
    """
    job_type_mapping = {
        JobType.TRACKED_PLAYER_UPDATER: TrackedPlayerUpdaterJob,
        JobType.MATCH_FETCHER: MatchFetcherJob,
        JobType.PLAYER_ANALYZER: PlayerAnalyzerJob,
        JobType.BAN_CHECKER: BanCheckerJob,
    }

    job_class = job_type_mapping.get(job.job_type)
    if not job_class:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown job type: {job.job_type}",
        )

    return job_class(job.id)


# === Job Configuration Endpoints ===


@router.get("/", response_model=list[JobConfigurationResponse])
async def list_job_configurations(
    job_service: JobServiceDep,
    active_only: bool = Query(False, description="Filter to active jobs only"),
):
    """
    List all job configurations.

    Args:
        active_only: If True, return only active jobs.

    Returns:
        List of job configurations.
    """
    try:
        jobs = await job_service.list_job_configurations(active_only=active_only)
        return jobs
    except Exception as e:
        logger.error("Failed to list job configurations", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving job configurations",
        )


@router.put("/{job_id}", response_model=JobConfigurationResponse)
async def update_job_configuration(
    job_id: int,
    job_update: JobConfigurationUpdate,
    job_service: JobServiceDep,
):
    """
    Update a job configuration.

    Args:
        job_id: Job configuration ID.
        job_update: Updated job configuration data.

    Returns:
        Updated job configuration.

    Raises:
        404: Job configuration not found.
    """
    try:
        job = await job_service.update_job_configuration(job_id, job_update)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job configuration with ID {job_id} not found",
            )
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update job configuration",
            job_id=job_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error updating job configuration",
        )


# === Job Execution Endpoints ===


@router.get("/{job_id}/executions", response_model=JobExecutionListResponse)
async def get_job_executions(
    job_id: int,
    job_service: JobServiceDep,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
):
    """
    Get execution history for a specific job.

    Args:
        job_id: Job configuration ID.
        page: Page number (1-indexed).
        size: Number of executions per page.
        status: Optional status filter.

    Returns:
        Paginated list of job executions.
    """
    try:
        executions = await job_service.list_job_executions(
            job_config_id=job_id,
            status=status,
            page=page,
            size=size,
        )
        return executions
    except Exception as e:
        logger.error(
            "Failed to list job executions",
            job_id=job_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving job executions",
        )


@router.get("/executions/all", response_model=JobExecutionListResponse)
async def list_all_executions(
    job_service: JobServiceDep,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
):
    """
    Get execution history for all jobs.

    Args:
        page: Page number (1-indexed).
        size: Number of executions per page.
        status: Optional status filter.

    Returns:
        Paginated list of all job executions.
    """
    try:
        executions = await job_service.list_job_executions(
            status=status,
            page=page,
            size=size,
        )
        return executions
    except Exception as e:
        logger.error("Failed to list all executions", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving all job executions",
        )


# === Job Control Endpoints ===


@router.post("/{job_id}/trigger", response_model=JobTriggerResponse)
async def trigger_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    job_service: JobServiceDep,
):
    """
    Manually trigger a job execution.

    This creates a new job execution record and triggers the job
    immediately, bypassing the normal schedule.

    Args:
        job_id: Job configuration ID.
        background_tasks: FastAPI background tasks for async execution.

    Returns:
        Job trigger response with execution ID.

    Raises:
        404: Job configuration not found.
        400: Job is not active or scheduler is disabled.
    """
    try:
        # Check if job exists and is active
        job = await job_service.get_job_configuration(job_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job configuration with ID {job_id} not found",
            )

        if not job.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Job '{job.name}' is not active and cannot be triggered",
            )

        # Create and trigger the job instance
        job_instance = _create_job_instance(job)
        background_tasks.add_task(job_instance.run)

        logger.info(
            "Job triggered manually",
            job_id=job_id,
            job_name=job.name,
            job_type=job.job_type.value,
        )

        return JobTriggerResponse(
            success=True,
            message=f"Job '{job.name}' triggered successfully",
            execution_id=None,  # Execution ID will be created by the job itself
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to trigger job",
            job_id=job_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error triggering job",
        )


@router.get("/status/overview", response_model=JobStatusResponse)
async def get_job_system_status(
    job_service: JobServiceDep,
):
    """
    Get overall job system status.

    Returns:
        Job system status including scheduler state, active jobs,
        running executions, and last execution details.
    """
    try:
        from app.core import get_global_settings

        settings = get_global_settings()

        # Get metrics
        active_jobs = await job_service.get_active_job_count()
        running_executions = await job_service.get_running_execution_count()
        last_execution = await job_service.get_latest_execution()

        # TODO: Get actual scheduler status and next run time from scheduler
        # For now, use config setting
        scheduler_running = settings.job_scheduler_enabled

        return JobStatusResponse(
            scheduler_running=scheduler_running,
            active_jobs=active_jobs,
            running_executions=running_executions,
            last_execution=last_execution,
            next_run_time=None,  # TODO: Get from scheduler
        )

    except Exception as e:
        logger.error("Failed to get job system status", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving job system status",
        )
