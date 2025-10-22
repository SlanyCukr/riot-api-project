"""Dependencies for the jobs feature."""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_db
from .service import JobService


async def get_job_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobService:
    """Get job service instance."""
    return JobService(db)


# Type aliases for cleaner dependency injection
JobServiceDep = Annotated[JobService, Depends(get_job_service)]

__all__ = ["get_job_service", "JobServiceDep"]
