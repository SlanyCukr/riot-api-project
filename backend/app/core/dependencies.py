"""Core dependencies for FastAPI application."""

from collections.abc import AsyncGenerator
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from . import get_db, get_riot_api_key
from .riot_api import RiotAPIClient, RiotDataManager
from .riot_api.constants import Platform, Region


async def get_riot_client(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncGenerator[RiotAPIClient, None]:
    """Get Riot API client instance."""
    # Get API key from database
    api_key = await get_riot_api_key(db)

    if not api_key:
        raise HTTPException(status_code=500, detail="Riot API key not configured")

    # Use default region/platform (hardcoded for EUN region)
    region = Region("europe")
    platform = Platform("eun1")

    client = RiotAPIClient(api_key=api_key, region=region, platform=platform)
    await client.start_session()
    try:
        yield client
    finally:
        await client.close()


async def get_riot_data_manager(
    db: Annotated[AsyncSession, Depends(get_db)],
    riot_client: Annotated[RiotAPIClient, Depends(get_riot_client)],
) -> RiotDataManager:
    """Get Riot data manager instance."""
    return RiotDataManager(db, riot_client)


# Type aliases for cleaner dependency injection
RiotDataManagerDep = Annotated[RiotDataManager, Depends(get_riot_data_manager)]

__all__ = ["get_riot_client", "get_riot_data_manager", "RiotDataManagerDep"]
