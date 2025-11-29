"""Dependency injection for matchmaking analysis feature."""

from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends

from app.core.database import get_db
from app.features.matchmaking_analysis.repository import (
    SQLAlchemyMatchmakingAnalysisRepository,
    MatchmakingAnalysisRepositoryInterface,
)
from app.features.matchmaking_analysis.service import MatchmakingAnalysisService
from app.core.dependencies import get_riot_client, get_riot_data_manager
from app.core.riot_api import RiotAPIClient
from app.core.riot_api.data_manager import RiotDataManager
from app.features.matchmaking_analysis.gateway import MatchmakingGateway
from app.features.matchmaking_analysis.transformers import (
    MatchmakingAnalysisTransformer,
)
from app.features.matchmaking_analysis.match_data_processor import MatchDataProcessor
from app.features.matchmaking_analysis.fairness_calculator import FairnessCalculator

# Database dependency
DatabaseDep = Annotated[AsyncSession, Depends(get_db)]


# Repository dependency
def get_matchmaking_analysis_repository(
    db: DatabaseDep,
) -> MatchmakingAnalysisRepositoryInterface:
    """Get matchmaking analysis repository instance.

    :param db: Database session
    :returns: Repository implementation
    """
    return SQLAlchemyMatchmakingAnalysisRepository(db)


MatchmakingAnalysisRepositoryDep = Annotated[
    MatchmakingAnalysisRepositoryInterface, Depends(get_matchmaking_analysis_repository)
]


# Gateway dependency
def get_matchmaking_gateway(
    riot_client: Annotated[RiotAPIClient, Depends(get_riot_client)],
    data_manager: Annotated[RiotDataManager, Depends(get_riot_data_manager)],
) -> MatchmakingGateway:
    """Get matchmaking gateway instance.

    :param riot_client: Riot API client
    :param data_manager: Riot data manager
    :returns: Gateway implementation
    """
    return MatchmakingGateway(riot_client, data_manager)


MatchmakingGatewayDep = Annotated[MatchmakingGateway, Depends(get_matchmaking_gateway)]


# Transformer dependency
def get_matchmaking_transformer() -> MatchmakingAnalysisTransformer:
    """Get matchmaking transformer instance (stateless).

    :returns: Transformer implementation
    """
    return MatchmakingAnalysisTransformer()


MatchmakingTransformerDep = Annotated[
    MatchmakingAnalysisTransformer, Depends(get_matchmaking_transformer)
]


# Match processor dependency
def get_match_processor() -> MatchDataProcessor:
    """Get match data processor instance.

    :returns: Processor implementation
    """
    return MatchDataProcessor()


MatchProcessorDep = Annotated[MatchDataProcessor, Depends(get_match_processor)]


# Fairness calculator dependency
def get_fairness_calculator() -> FairnessCalculator:
    """Get fairness calculator instance.

    :returns: Calculator implementation
    """
    return FairnessCalculator()


FairnessCalculatorDep = Annotated[FairnessCalculator, Depends(get_fairness_calculator)]


# Service dependency
def get_matchmaking_analysis_service(
    repository: MatchmakingAnalysisRepositoryDep,
    gateway: MatchmakingGatewayDep,
    transformer: MatchmakingTransformerDep,
    db: DatabaseDep,
) -> MatchmakingAnalysisService:
    """Get matchmaking analysis service instance with full DI.

    :param repository: Injected repository
    :param gateway: Injected gateway
    :param transformer: Injected transformer
    :param db: Database session
    :returns: Service implementation
    """
    return MatchmakingAnalysisService(
        repository=repository,
        gateway=gateway,
        transformer=transformer,
        db=db,
    )


MatchmakingAnalysisServiceDep = Annotated[
    MatchmakingAnalysisService, Depends(get_matchmaking_analysis_service)
]
