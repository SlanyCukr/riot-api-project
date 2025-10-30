import pytest
from unittest.mock import AsyncMock, MagicMock
from app.features.matchmaking_analysis.repository import (
    MatchmakingAnalysisRepositoryInterface,
    SQLAlchemyMatchmakingAnalysisRepository
)
from app.features.matchmaking_analysis.orm_models import JobExecutionORM
from app.features.matchmaking_analysis.schemas import MatchmakingAnalysisCreate

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def repository(mock_db):
    return SQLAlchemyMatchmakingAnalysisRepository(mock_db)

async def test_create_analysis(repository, mock_db):
    """Test creating a new matchmaking analysis"""
    # Setup
    create_data = MatchmakingAnalysisCreate(
        user_id="user-123",
        parameters={"region": "na", "queue": "ranked"}
    )

    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Execute
    result = await repository.create_analysis(create_data)

    # Verify
    assert isinstance(result, JobExecutionORM)
    assert result.user_id == "user-123"
    assert result.job_type == "matchmaking_analysis"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

async def test_get_analysis_by_id(repository, mock_db):
    """Test retrieving analysis by ID"""
    # Setup
    expected_job = JobExecutionORM(id="job-123", user_id="user-123", job_type="matchmaking_analysis")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expected_job
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Execute
    result = await repository.get_analysis_by_id("job-123")

    # Verify
    assert result == expected_job
    mock_db.execute.assert_called_once()

async def test_update_analysis_status(repository, mock_db):
    """Test updating analysis status"""
    # Setup
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()

    # Execute
    await repository.update_analysis_status("job-123", "running")

    # Verify
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()