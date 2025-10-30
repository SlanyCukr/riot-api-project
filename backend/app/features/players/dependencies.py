"""Dependencies for the players feature (REFACTORED).

Injects repository and gateway into service following dependency inversion principle.
"""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_db
from app.core.dependencies import get_riot_client
from app.core.riot_api.client import RiotAPIClient
from .gateway import RiotAPIGateway
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


async def get_riot_gateway(
    riot_client: Annotated[RiotAPIClient, Depends(get_riot_client)],
) -> RiotAPIGateway:
    """Get Riot API gateway instance.

    Creates an Anti-Corruption Layer that translates Riot API
    data structures to our domain models.

    :param riot_client: Riot API client
    :returns: Riot API gateway
    """
    return RiotAPIGateway(riot_client)


async def get_player_service(
    repository: Annotated[PlayerRepositoryInterface, Depends(get_player_repository)],
    gateway: Annotated[RiotAPIGateway, Depends(get_riot_gateway)],
) -> PlayerService:
    """Get player service instance (REFACTORED).

    Injects repository and gateway following dependency inversion principle.

    :param repository: Player repository
    :param gateway: Riot API gateway (Anti-Corruption Layer)
    :returns: Player service with injected dependencies
    """
    return PlayerService(repository, gateway)


# Type aliases for cleaner dependency injection
PlayerServiceDep = Annotated[PlayerService, Depends(get_player_service)]
PlayerRepositoryDep = Annotated[
    PlayerRepositoryInterface, Depends(get_player_repository)
]
RiotGatewayDep = Annotated[RiotAPIGateway, Depends(get_riot_gateway)]

__all__ = [
    "get_player_service",
    "get_player_repository",
    "get_riot_gateway",
    "PlayerServiceDep",
    "PlayerRepositoryDep",
    "RiotGatewayDep",
]
