"""Dependencies for the smurf detection feature."""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_db
from app.core.dependencies import RiotDataManagerDep
from .service import SmurfDetectionService


async def get_detection_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    riot_data_manager: RiotDataManagerDep,
) -> SmurfDetectionService:
    """Get smurf detection service instance."""
    return SmurfDetectionService(db, riot_data_manager)


# Type alias for cleaner dependency injection
DetectionServiceDep = Annotated[SmurfDetectionService, Depends(get_detection_service)]

__all__ = ["get_detection_service", "DetectionServiceDep"]
