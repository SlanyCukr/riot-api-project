"""Dependencies for the player analysis feature."""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_db
from app.core.dependencies import RiotDataManagerDep
from .service import PlayerAnalysisService
from .repository import SQLAlchemyPlayerAnalysisRepository


async def get_analysis_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SQLAlchemyPlayerAnalysisRepository:
    """Get player analysis repository instance."""
    return SQLAlchemyPlayerAnalysisRepository(db)


async def get_detection_service(
    repository: Annotated[
        SQLAlchemyPlayerAnalysisRepository, Depends(get_analysis_repository)
    ],
    riot_data_manager: RiotDataManagerDep,
) -> PlayerAnalysisService:
    """Get player analysis service instance."""
    return PlayerAnalysisService(repository, riot_data_manager)


# Type alias for cleaner dependency injection
AnalysisRepositoryDep = Annotated[
    SQLAlchemyPlayerAnalysisRepository, Depends(get_analysis_repository)
]
DetectionServiceDep = Annotated[PlayerAnalysisService, Depends(get_detection_service)]

__all__ = [
    "get_analysis_repository",
    "get_detection_service",
    "AnalysisRepositoryDep",
    "DetectionServiceDep",
]
