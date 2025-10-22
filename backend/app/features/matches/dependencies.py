"""Dependencies for the matches feature."""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from .service import MatchService


def get_match_service(db: AsyncSession = Depends(get_db)) -> MatchService:
    """
    Get match service instance.

    Args:
        db: Database session from dependency

    Returns:
        MatchService instance
    """
    return MatchService(db)


# Type alias for dependency injection
MatchServiceDep = Annotated[MatchService, Depends(get_match_service)]
