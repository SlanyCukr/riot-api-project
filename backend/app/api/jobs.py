"""Job management API endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.jobs import JobService
from ..models.job_tracking import JobStatus
from ..schemas.jobs import (
    JobConfigurationCreate,
    JobConfigurationUpdate,
    JobConfigurationResponse,
    JobExecutionResponse,
    JobExecutionListResponse,
    JobStatusResponse,
    JobTriggerResponse,
)
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


# Dependency for JobService
async def get_job_service(db: AsyncSession = Depends(get_db)) -> JobService:
    """Get job service instance."""
    return JobService(db)


# === Job Configuration Endpoints ===


@router.get("/", response_model=list[JobConfigurationResponse])
async def list_job_configurations(
    active_only: bool = Query(False, description="Filter to active jobs only"),
    job_service: JobService = Depends(get_job_service),
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
            detail=f"Failed to retrieve job configurations: {str(e)}",
        )


@router.get("/{job_id}", response_model=JobConfigurationResponse)
async def get_job_configuration(
    job_id: int,
    job_service: JobService = Depends(get_job_service),
):
    """
    Get a specific job configuration by ID.

    Args:
        job_id: Job configuration ID.

    Returns:
        Job configuration details.

    Raises:
        404: Job configuration not found.
    """
    try:
        job = await job_service.get_job_configuration(job_id)
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
            "Failed to get job configuration",
            job_id=job_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve job configuration: {str(e)}",
        )


@router.post("/", response_model=JobConfigurationResponse, status_code=201)
async def create_job_configuration(
    job_config: JobConfigurationCreate,
    job_service: JobService = Depends(get_job_service),
):
    """
    Create a new job configuration.

    Args:
        job_config: Job configuration data.

    Returns:
        Created job configuration.

    Raises:
        400: Job with the same name already exists.
    """
    try:
        job = await job_service.create_job_configuration(job_config)
        return job
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Failed to create job configuration",
            job_name=job_config.name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create job configuration: {str(e)}",
        )


@router.put("/{job_id}", response_model=JobConfigurationResponse)
async def update_job_configuration(
    job_id: int,
    job_update: JobConfigurationUpdate,
    job_service: JobService = Depends(get_job_service),
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
            detail=f"Failed to update job configuration: {str(e)}",
        )


@router.delete("/{job_id}", status_code=204)
async def delete_job_configuration(
    job_id: int,
    job_service: JobService = Depends(get_job_service),
):
    """
    Delete (soft delete) a job configuration.

    This sets is_active=False on the job configuration, preventing it
    from being scheduled but preserving the configuration and execution history.

    Args:
        job_id: Job configuration ID.

    Raises:
        404: Job configuration not found.
    """
    try:
        deleted = await job_service.delete_job_configuration(job_id)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Job configuration with ID {job_id} not found",
            )
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete job configuration",
            job_id=job_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete job configuration: {str(e)}",
        )


# === Job Execution Endpoints ===


@router.get("/{job_id}/executions", response_model=JobExecutionListResponse)
async def get_job_executions(
    job_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
    job_service: JobService = Depends(get_job_service),
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
            detail=f"Failed to retrieve job executions: {str(e)}",
        )


@router.get("/executions/all", response_model=JobExecutionListResponse)
async def list_all_executions(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
    job_service: JobService = Depends(get_job_service),
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
            detail=f"Failed to retrieve job executions: {str(e)}",
        )


@router.get("/executions/{execution_id}", response_model=JobExecutionResponse)
async def get_job_execution(
    execution_id: int,
    job_service: JobService = Depends(get_job_service),
):
    """
    Get details of a specific job execution.

    Args:
        execution_id: Job execution ID.

    Returns:
        Job execution details.

    Raises:
        404: Job execution not found.
    """
    try:
        execution = await job_service.get_job_execution(execution_id)
        if not execution:
            raise HTTPException(
                status_code=404,
                detail=f"Job execution with ID {execution_id} not found",
            )
        return execution
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get job execution",
            execution_id=execution_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve job execution: {str(e)}",
        )


# === Job Control Endpoints ===


@router.post("/{job_id}/trigger", response_model=JobTriggerResponse)
async def trigger_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    job_service: JobService = Depends(get_job_service),
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

        # Trigger the job execution in background
        from ..jobs.tracked_player_updater import TrackedPlayerUpdaterJob
        from ..jobs.player_analyzer import PlayerAnalyzerJob
        from ..models.job_tracking import JobType

        # Instantiate the appropriate job class
        if job.job_type == JobType.TRACKED_PLAYER_UPDATER:
            job_instance = TrackedPlayerUpdaterJob(job)
        elif job.job_type == JobType.PLAYER_ANALYZER:
            job_instance = PlayerAnalyzerJob(job)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown job type: {job.job_type}",
            )

        # Add job execution to background tasks
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
            detail=f"Failed to trigger job: {str(e)}",
        )


@router.get("/status/overview", response_model=JobStatusResponse)
async def get_job_system_status(
    job_service: JobService = Depends(get_job_service),
):
    """
    Get overall job system status.

    Returns:
        Job system status including scheduler state, active jobs,
        running executions, and last execution details.
    """
    try:
        from ..config import get_global_settings

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
            detail=f"Failed to retrieve job system status: {str(e)}",
        )
