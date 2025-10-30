import pytest
from unittest.mock import AsyncMock, MagicMock
from app.features.matchmaking_analysis.service_new import MatchmakingAnalysisService
from app.features.matchmaking_analysis.repository import (
    SQLAlchemyMatchmakingAnalysisRepository,
)
from app.features.matchmaking_analysis.gateway import MatchmakingGateway
from app.features.matchmaking_analysis.transformers import (
    MatchmakingAnalysisTransformer,
)
from app.features.matchmaking_analysis.schemas import MatchmakingAnalysisCreate


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_repository(mock_db):
    return AsyncMock(spec=SQLAlchemyMatchmakingAnalysisRepository)


@pytest.fixture
def mock_gateway():
    return AsyncMock(spec=MatchmakingGateway)


@pytest.fixture
def mock_transformer():
    return AsyncMock(spec=MatchmakingAnalysisTransformer)


@pytest.fixture
def service(mock_repository, mock_gateway, mock_transformer):
    return MatchmakingAnalysisService(
        repository=mock_repository, gateway=mock_gateway, transformer=mock_transformer
    )


async def test_service_initialization(
    service, mock_repository, mock_gateway, mock_transformer
):
    """Test service initialization with enterprise components"""
    assert service.repository == mock_repository
    assert service.gateway == mock_gateway
    assert service.transformer == mock_transformer


async def test_start_analysis_orchestration(
    service, mock_repository, mock_gateway, mock_transformer
):
    """Test service orchestration for starting analysis"""
    # Setup
    create_request = MatchmakingAnalysisCreate(
        user_id="user-123", parameters={"region": "na"}
    )

    mock_orm_job = MagicMock()
    mock_repository.create_analysis.return_value = mock_orm_job
    mock_transformer.orm_to_response.return_value = {"id": "job-123"}

    # Execute
    await service.start_analysis(create_request)

    # Verify orchestration
    mock_repository.create_analysis.assert_called_once_with(create_request)
    mock_transformer.orm_to_response.assert_called_once_with(mock_orm_job)
