"""
FastAPI dependencies for the Riot API application.
"""

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from ..database import get_db
from ..riot_api.client import RiotAPIClient
from ..riot_api.endpoints import Platform, Region
from ..services.players import PlayerService
from ..services.matches import MatchService
from ..services.stats import StatsService
from ..services.detection import SmurfDetectionService
from ..config import settings


async def get_riot_client() -> RiotAPIClient:
    """Get Riot API client instance."""
    if not settings.riot_api_key:
        raise HTTPException(status_code=500, detail="Riot API key not configured")

    # Convert string settings to enums
    region = Region(settings.riot_region.lower())
    platform = Platform(settings.riot_platform.lower())

    client = RiotAPIClient(
        api_key=settings.riot_api_key, region=region, platform=platform
    )
    await client.start_session()
    try:
        yield client
    finally:
        await client.close()


async def get_player_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    riot_client: Annotated[RiotAPIClient, Depends(get_riot_client)],
) -> PlayerService:
    """Get player service instance."""
    return PlayerService(db, riot_client)


async def get_match_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    riot_client: Annotated[RiotAPIClient, Depends(get_riot_client)],
) -> MatchService:
    """Get match service instance."""
    return MatchService(db, riot_client)


async def get_stats_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StatsService:
    """Get stats service instance."""
    return StatsService(db)


async def get_detection_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    riot_client: Annotated[RiotAPIClient, Depends(get_riot_client)],
) -> SmurfDetectionService:
    """Get smurf detection service instance."""
    return SmurfDetectionService(db, riot_client)


# Type aliases for cleaner dependency injection
DBSession = Annotated[AsyncSession, Depends(get_db)]
RiotClient = Annotated[RiotAPIClient, Depends(get_riot_client)]
PlayerServiceDep = Annotated[PlayerService, Depends(get_player_service)]
MatchServiceDep = Annotated[MatchService, Depends(get_match_service)]
StatsServiceDep = Annotated[StatsService, Depends(get_stats_service)]
DetectionServiceDep = Annotated[SmurfDetectionService, Depends(get_detection_service)]
