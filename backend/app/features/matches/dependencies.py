"""Dependencies for the matches feature (REFACTORED).

Injects repository and gateway into service following dependency inversion principle.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_riot_client
from app.core.riot_api.client import RiotAPIClient

from .gateway import RiotMatchGateway
from .repository import (
    MatchParticipantRepositoryInterface,
    MatchRepositoryInterface,
    SQLAlchemyMatchParticipantRepository,
    SQLAlchemyMatchRepository,
)
from .service import MatchService


async def get_match_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MatchRepositoryInterface:
    """Get match repository instance.

    :param db: Database session
    :returns: Match repository implementation
    """
    return SQLAlchemyMatchRepository(db)


async def get_match_participant_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MatchParticipantRepositoryInterface:
    """Get match participant repository instance.

    :param db: Database session
    :returns: Match participant repository implementation
    """
    return SQLAlchemyMatchParticipantRepository(db)


async def get_riot_match_gateway(
    riot_client: Annotated[RiotAPIClient, Depends(get_riot_client)],
) -> RiotMatchGateway:
    """Get Riot match gateway instance.

    Creates an Anti-Corruption Layer that translates Riot API
    data structures to our domain models.

    :param riot_client: Riot API client
    :returns: Riot match gateway
    """
    return RiotMatchGateway(riot_client)


async def get_match_service(
    repository: Annotated[MatchRepositoryInterface, Depends(get_match_repository)],
    participant_repository: Annotated[
        MatchParticipantRepositoryInterface, Depends(get_match_participant_repository)
    ],
    gateway: Annotated[RiotMatchGateway, Depends(get_riot_match_gateway)],
) -> MatchService:
    """Get match service instance (REFACTORED).

    Injects repository and gateway following dependency inversion principle.

    :param repository: Match repository
    :param participant_repository: Match participant repository
    :param gateway: Riot match gateway (Anti-Corruption Layer)
    :returns: Match service with injected dependencies
    """
    return MatchService(repository, participant_repository, gateway)


# Legacy dependency for backward compatibility (used by jobs)
async def get_match_service_legacy(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MatchService:
    """Get match service instance (legacy mode).

    For backward compatibility with jobs that expect AsyncSession.
    Creates repositories internally.

    :param db: Database session
    :returns: Match service instance with legacy initialization
    """
    return MatchService(db)


# Type aliases for cleaner dependency injection
MatchServiceDep = Annotated[MatchService, Depends(get_match_service)]
MatchRepositoryDep = Annotated[MatchRepositoryInterface, Depends(get_match_repository)]
MatchParticipantRepositoryDep = Annotated[
    MatchParticipantRepositoryInterface, Depends(get_match_participant_repository)
]
RiotMatchGatewayDep = Annotated[RiotMatchGateway, Depends(get_riot_match_gateway)]
MatchServiceLegacyDep = Annotated[MatchService, Depends(get_match_service_legacy)]

__all__ = [
    "get_match_service",
    "get_match_repository",
    "get_match_participant_repository",
    "get_riot_match_gateway",
    "get_match_service_legacy",
    "MatchServiceDep",
    "MatchRepositoryDep",
    "MatchParticipantRepositoryDep",
    "RiotMatchGatewayDep",
    "MatchServiceLegacyDep",
]
