"""Dependencies for the matchmaking analysis feature."""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_db
from app.core.riot_api.client import RiotAPIClient
from app.core.dependencies import get_riot_client
from .service import MatchmakingAnalysisService


async def get_matchmaking_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    riot_client: Annotated[RiotAPIClient, Depends(get_riot_client)],
) -> MatchmakingAnalysisService:
    """Get matchmaking analysis service instance."""
    return MatchmakingAnalysisService(db, riot_client)


# Type alias for cleaner dependency injection
MatchmakingServiceDep = Annotated[
    MatchmakingAnalysisService, Depends(get_matchmaking_service)
]

__all__ = ["get_matchmaking_service", "MatchmakingServiceDep"]
