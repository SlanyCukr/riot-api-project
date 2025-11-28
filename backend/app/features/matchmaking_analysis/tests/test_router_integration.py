"""
Integration tests for matchmaking analysis router using modern enterprise architecture patterns.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.features.matchmaking_analysis.schemas import (
    MatchmakingAnalysisCreate,
    MatchmakingAnalysisResponse,
)
from app.features.matchmaking_analysis.service import MatchmakingAnalysisService
from app.features.matchmaking_analysis.dependencies import (
    MatchmakingAnalysisServiceDep,
    get_matchmaking_analysis_service,
    get_matchmaking_analysis_repository,
    get_matchmaking_gateway,
    MatchmakingAnalysisRepositoryDep,
    MatchmakingGatewayDep,
)
from app.core.dependencies import get_riot_client, get_riot_data_manager
from app.core.database import get_db
from app.core.riot_api import RiotAPIClient
from app.core.riot_api.data_manager import RiotDataManager
from app.features.matchmaking_analysis.gateway import MatchmakingGateway
from app.features.matchmaking_analysis.transformers import (
    MatchmakingAnalysisTransformer,
)
from app.features.matchmaking_analysis.repository import MatchmakingAnalysisRepositoryInterface

# Apply pytest-asyncio for proper async testing
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_enterprise_stack():
    """Create comprehensive mock for entire enterprise architecture stack."""
    # Mock repository layer
    mock_repository = AsyncMock(spec=MatchmakingAnalysisRepositoryInterface)
    mock_repository.create_analysis = AsyncMock()
    mock_repository.get_analysis_by_id = AsyncMock()
    mock_repository.get_user_analyses = AsyncMock()

    # Mock gateway layer
    mock_gateway = AsyncMock(spec=MatchmakingGateway)

    # Mock transformer layer
    mock_transformer = AsyncMock(spec=MatchmakingAnalysisTransformer)

    # Mock database session (to prevent real database calls)
    mock_db = AsyncMock(spec=AsyncSession)

    # Mock Riot API client with proper async context manager behavior
    mock_riot_client = AsyncMock(spec=RiotAPIClient)
    mock_riot_client.start_session = AsyncMock()
    mock_riot_client.close = AsyncMock()
    mock_riot_client.__aenter__ = AsyncMock(return_value=mock_riot_client)
    mock_riot_client.__aexit__ = AsyncMock(return_value=None)

    # Mock Riot data manager
    mock_data_manager = AsyncMock(spec=RiotDataManager)

    return {
        'repository': mock_repository,
        'gateway': mock_gateway,
        'transformer': mock_transformer,
        'db': mock_db,
        'riot_client': mock_riot_client,
        'data_manager': mock_data_manager
    }


@pytest.fixture
def test_client_with_fastapi_pattern_overrides(mock_enterprise_stack):
    """Test client using exact FastAPI dependency override patterns from documentation."""
    # Store original state
    original_overrides = app.dependency_overrides.copy()
    
    # Clear all overrides
    app.dependency_overrides.clear()
    
    # Create override functions that exactly match the dependency signatures
    async def override_get_db():
        """Override database dependency."""
        yield mock_enterprise_stack['db']
    
    async def override_get_riot_client():
        """Override Riot API client dependency."""
        yield mock_enterprise_stack['riot_client']
    
    def override_get_riot_data_manager():
        """Override Riot data manager dependency."""
        return mock_enterprise_stack['data_manager']
    
    def override_get_repository():
        """Override repository dependency."""
        return mock_enterprise_stack['repository']
    
    def override_get_gateway():
        """Override gateway dependency."""
        return mock_enterprise_stack['gateway']
    
    def override_get_service():
        """Override service dependency with mocked dependencies."""
        return MatchmakingAnalysisService(
            repository=mock_enterprise_stack['repository'],
            gateway=mock_enterprise_stack['gateway'],
            transformer=mock_enterprise_stack['transformer'],
            db=mock_enterprise_stack['db']
        )
    
    # Apply overrides using the exact function references
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_riot_client] = override_get_riot_client
    app.dependency_overrides[get_riot_data_manager] = override_get_riot_data_manager
    app.dependency_overrides[get_matchmaking_analysis_repository] = override_get_repository
    app.dependency_overrides[get_matchmaking_gateway] = override_get_gateway
    app.dependency_overrides[get_matchmaking_analysis_service] = override_get_service
    
    # Create test client
    with TestClient(app) as client:
        yield client
    
    # Cleanup
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)


class TestMatchmakingAnalysisRouterComprehensive:
    """Test suite for matchmaking analysis router with comprehensive enterprise mocking."""

    async def test_start_analysis_endpoint_success(
        self,
        test_client_with_fastapi_pattern_overrides,
        mock_enterprise_stack,
    ):
        """Test successful analysis start with properly mocked enterprise stack."""
        # Mock repository response
        mock_job_orm = MagicMock()
        mock_job_orm.id = "job-123"
        mock_job_orm.user_id = "user-123"
        mock_job_orm.job_type = "matchmaking_analysis"
        mock_job_orm.status = "pending"
        mock_job_orm.parameters = {"region": "na"}
        mock_job_orm.result = None
        mock_job_orm.error_message = None
        mock_job_orm.progress = 0.0
        mock_job_orm.created_at = "2025-10-31T20:00:00Z"
        mock_job_orm.started_at = None
        mock_job_orm.completed_at = None
        mock_job_orm.matches_analyzed = 0
        mock_job_orm.winrate = None
        mock_job_orm.avg_rank_difference = None
        mock_job_orm.fairness_score = None

        mock_enterprise_stack['repository'].create_analysis.return_value = mock_job_orm

        # Mock transformer response - must return Pydantic object (router accesses .id)
        expected_response = MatchmakingAnalysisResponse(
            id="job-123",
            user_id="user-123",
            job_type="matchmaking_analysis",
            status="pending",
            parameters={"region": "na"},
            result=None,
            error_message=None,
            progress=0.0,
            created_at="2025-10-31T20:00:00Z",
            started_at=None,
            completed_at=None,
            matches_analyzed=0,
            winrate=None,
            avg_rank_difference=None,
            fairness_score=None,
        )
        mock_enterprise_stack['transformer'].orm_to_response.return_value = expected_response

        # Execute request
        response = test_client_with_fastapi_pattern_overrides.post(
            "/api/v1/matchmaking-analysis/start",
            json={"user_id": "user-123", "parameters": {"region": "na"}},
        )

        # Debug: Check response
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.content}")
        if response.status_code != 201:
            print(f"Error response: {response.json()}")

        # Verify response (201 Created is correct for POST that creates a resource)
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["id"] == "job-123"
        assert response_data["user_id"] == "user-123"
        assert response_data["status"] == "pending"
        assert response_data["parameters"]["region"] == "na"

        # Verify enterprise stack was called correctly
        mock_enterprise_stack['repository'].create_analysis.assert_called_once()
        mock_enterprise_stack['transformer'].orm_to_response.assert_called_once_with(mock_job_orm)

    async def test_get_analysis_status_endpoint_success(
        self,
        test_client_with_fastapi_pattern_overrides,
        mock_enterprise_stack,
    ):
        """Test successful analysis status retrieval with proper mocking."""
        # Mock repository response
        mock_job_orm = MagicMock()
        mock_job_orm.id = "job-123"
        mock_job_orm.user_id = "user-123"
        mock_job_orm.job_type = "matchmaking_analysis"
        mock_job_orm.status = "in_progress"
        mock_job_orm.parameters = {"region": "na"}
        mock_job_orm.result = None
        mock_job_orm.error_message = None
        mock_job_orm.progress = 45.5
        mock_job_orm.created_at = "2025-10-31T20:00:00Z"
        mock_job_orm.started_at = "2025-10-31T20:01:00Z"
        mock_job_orm.completed_at = None
        mock_job_orm.matches_analyzed = 5
        mock_job_orm.winrate = None
        mock_job_orm.avg_rank_difference = None
        mock_job_orm.fairness_score = None

        mock_enterprise_stack['repository'].get_analysis_by_id.return_value = mock_job_orm

        # Mock transformer response
        expected_response_data = {
            "id": "job-123",
            "user_id": "user-123",
            "job_type": "matchmaking_analysis",
            "status": "in_progress",
            "parameters": {"region": "na"},
            "result": None,
            "error_message": None,
            "progress": 45.5,
            "created_at": "2025-10-31T20:00:00Z",
            "started_at": "2025-10-31T20:01:00Z",
            "completed_at": None,
            "matches_analyzed": 5,
            "winrate": None,
            "avg_rank_difference": None,
            "fairness_score": None,
        }
        mock_enterprise_stack['transformer'].orm_to_response.return_value = expected_response_data

        # Execute request
        response = test_client_with_fastapi_pattern_overrides.get("/api/v1/matchmaking-analysis/job/job-123/status")

        # Debug: Check response
        print(f"Status response status: {response.status_code}")
        print(f"Status response content: {response.content}")
        if response.status_code != 200:
            print(f"Error response: {response.json()}")

        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == "job-123"
        assert response_data["user_id"] == "user-123"
        assert response_data["status"] == "in_progress"
        assert response_data["progress"] == 45.5
        assert response_data["matches_analyzed"] == 5
        assert response_data["parameters"]["region"] == "na"

        # Verify enterprise stack was called correctly
        mock_enterprise_stack['repository'].get_analysis_by_id.assert_called_once_with("job-123")
        mock_enterprise_stack['transformer'].orm_to_response.assert_called_once_with(mock_job_orm)

    async def test_get_analysis_status_endpoint_not_found(
        self,
        test_client_with_fastapi_pattern_overrides,
        mock_enterprise_stack,
    ):
        """Test analysis status endpoint when job not found."""
        # Mock repository to return None (job not found)
        mock_enterprise_stack['repository'].get_analysis_by_id.return_value = None

        # Execute request with non-existent job ID
        response = test_client_with_fastapi_pattern_overrides.get("/api/v1/matchmaking-analysis/job/non-existent-job/status")

        # Debug: Check response
        print(f"Not found response status: {response.status_code}")
        print(f"Not found response content: {response.content}")

        # Verify 404 response
        assert response.status_code == 404

        # Verify repository was called correctly
        mock_enterprise_stack['repository'].get_analysis_by_id.assert_called_once_with("non-existent-job")

        # Verify transformer was not called (since no job was found)
        mock_enterprise_stack['transformer'].orm_to_response.assert_not_called()

    async def test_get_user_analyses_endpoint_success(
        self,
        test_client_with_fastapi_pattern_overrides,
        mock_enterprise_stack,
    ):
        """Test successful user analyses retrieval."""
        # Mock repository response
        mock_job_orm_1 = MagicMock()
        mock_job_orm_1.id = "job-123"
        mock_job_orm_1.user_id = "user-123"
        mock_job_orm_1.job_type = "matchmaking_analysis"
        mock_job_orm_1.status = "completed"
        mock_job_orm_1.parameters = {"region": "na"}
        mock_job_orm_1.result = None
        mock_job_orm_1.error_message = None
        mock_job_orm_1.progress = 100.0
        mock_job_orm_1.created_at = "2025-10-31T20:00:00Z"
        mock_job_orm_1.started_at = "2025-10-31T20:01:00Z"
        mock_job_orm_1.completed_at = "2025-10-31T20:05:00Z"
        mock_job_orm_1.matches_analyzed = 10
        mock_job_orm_1.winrate = 0.7
        mock_job_orm_1.avg_rank_difference = 20.0
        mock_job_orm_1.fairness_score = 0.8

        mock_job_orm_2 = MagicMock()
        mock_job_orm_2.id = "job-124"
        mock_job_orm_2.user_id = "user-123"
        mock_job_orm_2.job_type = "matchmaking_analysis"
        mock_job_orm_2.status = "pending"
        mock_job_orm_2.parameters = {"region": "na"}
        mock_job_orm_2.result = None
        mock_job_orm_2.error_message = None
        mock_job_orm_2.progress = 0.0
        mock_job_orm_2.created_at = "2025-10-31T20:10:00Z"
        mock_job_orm_2.started_at = None
        mock_job_orm_2.completed_at = None
        mock_job_orm_2.matches_analyzed = 0
        mock_job_orm_2.winrate = None
        mock_job_orm_2.avg_rank_difference = None
        mock_job_orm_2.fairness_score = None

        mock_enterprise_stack['repository'].get_user_analyses.return_value = [mock_job_orm_1, mock_job_orm_2]

        # Mock transformer responses
        def mock_transform(orm_obj):
            if orm_obj.id == "job-123":
                return {
                    "id": "job-123",
                    "user_id": "user-123",
                    "job_type": "matchmaking_analysis",
                    "status": "completed",
                    "parameters": {"region": "na"},
                    "result": None,
                    "error_message": None,
                    "progress": 100.0,
                    "created_at": "2025-10-31T20:00:00Z",
                    "started_at": "2025-10-31T20:01:00Z",
                    "completed_at": "2025-10-31T20:05:00Z",
                    "matches_analyzed": 10,
                    "winrate": 0.7,
                    "avg_rank_difference": 20.0,
                    "fairness_score": 0.8,
                }
            else:
                return {
                    "id": "job-124",
                    "user_id": "user-123",
                    "job_type": "matchmaking_analysis",
                    "status": "pending",
                    "parameters": {"region": "na"},
                    "result": None,
                    "error_message": None,
                    "progress": 0.0,
                    "created_at": "2025-10-31T20:10:00Z",
                    "started_at": None,
                    "completed_at": None,
                    "matches_analyzed": 0,
                    "winrate": None,
                    "avg_rank_difference": None,
                    "fairness_score": None,
                }

        mock_enterprise_stack['transformer'].orm_to_response.side_effect = mock_transform

        # Execute request
        response = test_client_with_fastapi_pattern_overrides.get("/api/v1/matchmaking-analysis/user/user-123/analyses")

        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data["analyses"]) == 2
        assert response_data["analyses"][0]["id"] == "job-123"
        assert response_data["analyses"][1]["id"] == "job-124"

        # Verify repository was called correctly
        mock_enterprise_stack['repository'].get_user_analyses.assert_called_once_with("user-123", 50)

    async def test_start_analysis_endpoint_validation_error(
        self,
        test_client_with_fastapi_pattern_overrides,
    ):
        """Test analysis start endpoint with invalid request data."""
        # Execute request with missing required field
        response = test_client_with_fastapi_pattern_overrides.post(
            "/api/v1/matchmaking-analysis/start",
            json={"parameters": {"region": "na"}},  # Missing user_id
        )

        # Verify validation error
        assert response.status_code == 422
        error_details = response.json()["detail"]
        assert len(error_details) > 0
        # Check that user_id field is mentioned in the error
        user_id_error = next((error for error in error_details if "user_id" in error.get("loc", [])), None)
        assert user_id_error is not None