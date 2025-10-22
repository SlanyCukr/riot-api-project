"""Jobs feature - Background job management and execution."""

from .router import router as jobs_router
from .service import JobService
from .models import JobConfiguration, JobExecution, JobStatus, JobType
from .schemas import (
    JobConfigurationResponse,
    JobConfigurationUpdate,
    JobExecutionResponse,
    JobStatusResponse,
    JobTriggerResponse,
)
from .scheduler import start_scheduler, shutdown_scheduler, get_scheduler
from .log_capture import job_log_capture

__all__ = [
    # Router
    "jobs_router",
    # Service
    "JobService",
    # Models
    "JobConfiguration",
    "JobExecution",
    "JobStatus",
    "JobType",
    # Schemas
    "JobConfigurationResponse",
    "JobConfigurationUpdate",
    "JobExecutionResponse",
    "JobStatusResponse",
    "JobTriggerResponse",
    # Scheduler
    "start_scheduler",
    "shutdown_scheduler",
    "get_scheduler",
    # Utilities
    "job_log_capture",
]
