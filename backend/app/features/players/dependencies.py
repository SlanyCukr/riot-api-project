"""Dependencies for the players feature."""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_db
from app.core.dependencies import RiotDataManagerDep
from .service import PlayerService


async def get_player_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PlayerService:
    """Get player service instance."""
    return PlayerService(db)


# Type aliases for cleaner dependency injection
PlayerServiceDep = Annotated[PlayerService, Depends(get_player_service)]

__all__ = ["get_player_service", "PlayerServiceDep", "RiotDataManagerDep"]
