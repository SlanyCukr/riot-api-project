"""Dependencies for the players feature (REFACTORED).

Injects repository into service following dependency inversion principle.
"""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_db
from app.core.dependencies import RiotDataManagerDep
from .service import PlayerService
from .repository import SQLAlchemyPlayerRepository, PlayerRepositoryInterface


async def get_player_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PlayerRepositoryInterface:
    """Get player repository instance.

    :param db: Database session
    :returns: Player repository implementation
    """
    return SQLAlchemyPlayerRepository(db)


async def get_player_service(
    repository: Annotated[PlayerRepositoryInterface, Depends(get_player_repository)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PlayerService:
    """Get player service instance (REFACTORED).

    Injects repository following dependency inversion principle.

    :param repository: Player repository
    :param db: Database session (for legacy methods during transition)
    :returns: Player service with injected dependencies
    """
    return PlayerService(repository, db)


# Type aliases for cleaner dependency injection
PlayerServiceDep = Annotated[PlayerService, Depends(get_player_service)]
PlayerRepositoryDep = Annotated[
    PlayerRepositoryInterface, Depends(get_player_repository)
]

__all__ = [
    "get_player_service",
    "get_player_repository",
    "PlayerServiceDep",
    "PlayerRepositoryDep",
    "RiotDataManagerDep",
]
