import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@patch("app.core.dependencies.get_riot_client")
@patch("app.features.matchmaking_analysis.dependencies.get_matchmaking_gateway")
@patch(
    "app.features.matchmaking_analysis.dependencies.get_matchmaking_analysis_service"
)
def test_start_analysis_endpoint(
    mock_get_service, mock_get_gateway, mock_get_riot_client, client
):
    """Test start analysis endpoint uses new enterprise service"""
    # Setup - mock the Riot API client to avoid API key requirement
    mock_riot_client = MagicMock()
    mock_get_riot_client.return_value = mock_riot_client

    mock_gateway = MagicMock()
    mock_get_gateway.return_value = mock_gateway

    mock_service = AsyncMock()
    mock_service.start_analysis.return_value = {
        "id": "job-123",
        "status": "pending",
        "user_id": "user-123",
    }
    mock_get_service.return_value = mock_service

    # Execute
    response = client.post(
        "/api/v1/matchmaking-analysis/start",
        json={"user_id": "user-123", "parameters": {"region": "na"}},
    )

    # Verify
    assert response.status_code == 200
    assert response.json()["id"] == "job-123"
    mock_service.start_analysis.assert_called_once()


@patch(
    "app.features.matchmaking_analysis.dependencies.get_matchmaking_analysis_service"
)
def test_get_analysis_status_endpoint(mock_get_service, client):
    """Test get analysis status endpoint uses new enterprise service"""
    # Setup
    mock_service = AsyncMock()
    mock_service.get_analysis_status.return_value = {
        "id": "job-123",
        "status": "running",
        "progress": 50.0,
    }
    mock_get_service.return_value = mock_service

    # Execute
    response = client.get("/api/v1/matchmaking-analysis/job-123/status")

    # Verify
    assert response.status_code == 200
    assert response.json()["status"] == "running"
    mock_service.get_analysis_status.assert_called_once_with("job-123")
