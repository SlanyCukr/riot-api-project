import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.enums import JobStatus
from app.features.matchmaking_analysis.repository import (
    SQLAlchemyMatchmakingAnalysisRepository,
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
        user_id="user-123", parameters={"region": "na", "queue": "ranked"}
    )

    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()  # Repository uses flush(), not commit()
    mock_db.refresh = AsyncMock()

    # Execute
    result = await repository.create_analysis(create_data)

    # Verify
    assert isinstance(result, JobExecutionORM)
    assert result.user_id == "user-123"
    assert result.job_type == "matchmaking_analysis"
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()  # Repository doesn't commit, service does
    mock_db.refresh.assert_called_once()


async def test_get_analysis_by_id(repository, mock_db):
    """Test retrieving analysis by ID"""
    # Setup
    expected_job = JobExecutionORM(
        id="job-123", user_id="user-123", job_type="matchmaking_analysis"
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expected_job
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Execute
    result = await repository.get_analysis_by_id("job-123")

    # Verify
    assert result == expected_job
    mock_db.execute.assert_called_once()


async def test_update_analysis_status(repository, mock_db):
    """Test updating analysis status with row-level locking"""
    # Setup - mock the get_analysis_by_id to return a job
    expected_job = JobExecutionORM(
        id="job-123",
        user_id="user-123",
        job_type="matchmaking_analysis",
        status=JobStatus.PENDING,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expected_job
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()  # Repository uses flush(), not commit()

    # Execute
    result = await repository.update_analysis_status("job-123", JobStatus.RUNNING)

    # Verify
    assert result is not None
    assert result.status == JobStatus.RUNNING
    mock_db.execute.assert_called_once()  # Called for SELECT with FOR UPDATE
    mock_db.flush.assert_called_once()  # Repository doesn't commit, service does


def test_repository_interface_implementation(repository):
    """Test that SQLAlchemy repository implements all required interface methods"""
    # Verify all expected interface methods are present and callable
    expected_methods = {
        "create_analysis",
        "get_analysis_by_id",
        "update_analysis_status",
        "update_analysis_progress",
        "get_user_analyses",
        "save_analysis_results",
    }

    for method_name in expected_methods:
        assert hasattr(repository, method_name), f"Repository missing method: {method_name}"
        method = getattr(repository, method_name)
        assert callable(method), f"Repository method not callable: {method_name}"

    # Verify the repository has a db property
    assert hasattr(repository, "db"), "Repository missing db property"
