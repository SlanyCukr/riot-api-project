"""Dependencies for the player analysis feature."""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_db
from app.core.dependencies import RiotDataManagerDep
from .service import PlayerAnalysisService


async def get_detection_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    riot_data_manager: RiotDataManagerDep,
) -> PlayerAnalysisService:
    """Get player analysis service instance."""
    return PlayerAnalysisService(db, riot_data_manager)


# Type alias for cleaner dependency injection
DetectionServiceDep = Annotated[PlayerAnalysisService, Depends(get_detection_service)]

__all__ = ["get_detection_service", "DetectionServiceDep"]
