from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends

from app.core.database import get_db
from app.features.matchmaking_analysis.repository import (
    SQLAlchemyMatchmakingAnalysisRepository,
    MatchmakingAnalysisRepositoryInterface,
)
from app.features.matchmaking_analysis.service_new import MatchmakingAnalysisService
from app.core.riot_api import RiotAPIClient
from app.core.riot_api.data_manager import RiotDataManager
from app.features.matchmaking_analysis.gateway import MatchmakingGateway
from app.features.matchmaking_analysis.transformers import (
    MatchmakingAnalysisTransformer,
)

# Database dependency
DatabaseDep = Annotated[AsyncSession, Depends(get_db)]


# Repository dependency
def get_matchmaking_analysis_repository(
    db: DatabaseDep,
) -> MatchmakingAnalysisRepositoryInterface:
    return SQLAlchemyMatchmakingAnalysisRepository(db)


MatchmakingAnalysisRepositoryDep = Annotated[
    MatchmakingAnalysisRepositoryInterface, Depends(get_matchmaking_analysis_repository)
]


# Gateway dependency
def get_matchmaking_gateway(
    riot_client: Annotated[RiotAPIClient, Depends()],
    data_manager: Annotated[RiotDataManager, Depends()],
) -> MatchmakingGateway:
    return MatchmakingGateway(riot_client, data_manager)


MatchmakingGatewayDep = Annotated[MatchmakingGateway, Depends(get_matchmaking_gateway)]


# Service dependency
def get_matchmaking_analysis_service(
    repository: MatchmakingAnalysisRepositoryDep, gateway: MatchmakingGatewayDep
) -> MatchmakingAnalysisService:
    transformer = MatchmakingAnalysisTransformer()
    return MatchmakingAnalysisService(repository, gateway, transformer)


MatchmakingAnalysisServiceDep = Annotated[
    MatchmakingAnalysisService, Depends(get_matchmaking_analysis_service)
]
