"""
Test cases for the detection API endpoints.

Tests for new and existing endpoints that are now being actively used.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.detection import DetectionResponse, DetectionFactor
from app.models.smurf_detection import SmurfDetection


@pytest.fixture
def mock_detection_service():
    """Mock detection service for testing."""
    service = AsyncMock()
    return service


@pytest.fixture
def sample_detection_response():
    """Sample detection response for testing."""
    return DetectionResponse(
        puuid="sample-puuid-123",
        is_smurf=True,
        detection_score=0.75,
        confidence_level="high",
        factors=[
            DetectionFactor(
                name="win_rate",
                value=0.70,
                meets_threshold=True,
                weight=0.35,
                description="High win rate: 70%",
                score=0.8,
            ),
            DetectionFactor(
                name="account_level",
                value=25.0,
                meets_threshold=True,
                weight=0.15,
                description="Low account level: 25",
                score=0.15,
            ),
        ],
        reason="High win rate, low account level",
        sample_size=30,
        analysis_time_seconds=1.5,
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_detection_db():
    """Sample detection database model for testing."""
    return SmurfDetection(
        id=1,
        puuid="sample-puuid-123",
        is_smurf=True,
        confidence="high",
        smurf_score=Decimal("0.75"),
        games_analyzed=30,
        queue_type="420",
        win_rate_score=0.8,
        kda_score=0.6,
        account_level_score=0.15,
        rank_discrepancy_score=0.5,
        account_level=25,
        current_tier="GOLD",
        current_rank="II",
        analysis_version="1.0",
        created_at=datetime.now(),
        last_analysis=datetime.now(),
    )


class TestDetectionLatestEndpoint:
    """Test /player/{puuid}/latest endpoint."""

    def test_get_latest_detection_returns_cached(
        self, mock_detection_service, sample_detection_response, sample_detection_db
    ):
        """Test returns cached detection result."""
        # Setup mock
        mock_detection_service._get_recent_detection.return_value = sample_detection_db
        mock_detection_service._convert_to_response.return_value = (
            sample_detection_response
        )

        # Override dependency
        from app.api.dependencies import get_detection_service

        app.dependency_overrides[get_detection_service] = lambda: mock_detection_service

        with TestClient(app) as client:
            response = client.get("/detection/player/sample-puuid-123/latest")

            assert response.status_code == 200
            data = response.json()
            assert data["puuid"] == "sample-puuid-123"
            assert data["is_smurf"] is True
            assert data["detection_score"] == 0.75
            assert data["confidence_level"] == "high"

            # Verify service was called
            mock_detection_service._get_recent_detection.assert_called_once()

        # Clean up
        app.dependency_overrides.clear()

    def test_get_latest_detection_performs_new_analysis(
        self, mock_detection_service, sample_detection_response
    ):
        """Test performs new analysis if no cached result."""
        # Setup mock - no recent detection
        mock_detection_service._get_recent_detection.return_value = None
        mock_detection_service.analyze_player.return_value = sample_detection_response

        # Override dependency
        from app.api.dependencies import get_detection_service

        app.dependency_overrides[get_detection_service] = lambda: mock_detection_service

        with TestClient(app) as client:
            response = client.get("/detection/player/sample-puuid-123/latest")

            assert response.status_code == 200
            data = response.json()
            assert data["puuid"] == "sample-puuid-123"

            # Verify new analysis was performed
            mock_detection_service.analyze_player.assert_called_once()

        # Clean up
        app.dependency_overrides.clear()

    def test_get_latest_detection_force_refresh(
        self, mock_detection_service, sample_detection_response
    ):
        """Test force refresh performs new analysis."""
        # Setup mock
        mock_detection_service.analyze_player.return_value = sample_detection_response

        # Override dependency
        from app.api.dependencies import get_detection_service

        app.dependency_overrides[get_detection_service] = lambda: mock_detection_service

        with TestClient(app) as client:
            response = client.get(
                "/detection/player/sample-puuid-123/latest?force_refresh=true"
            )

            assert response.status_code == 200

            # Should call analyze_player directly, not check cache
            mock_detection_service.analyze_player.assert_called_once()

        # Clean up
        app.dependency_overrides.clear()

    def test_get_latest_detection_not_found(self, mock_detection_service):
        """Test returns 404 if player not found."""
        # Setup mock to raise ValueError
        mock_detection_service._get_recent_detection.return_value = None
        mock_detection_service.analyze_player.side_effect = ValueError(
            "Player not found"
        )

        # Override dependency
        from app.api.dependencies import get_detection_service

        app.dependency_overrides[get_detection_service] = lambda: mock_detection_service

        with TestClient(app) as client:
            response = client.get("/detection/player/missing-puuid/latest")

            assert response.status_code == 404
            data = response.json()
            assert "Player not found" in data["detail"]

        # Clean up
        app.dependency_overrides.clear()


class TestDetectionAnalyzeEndpoint:
    """Test /detection/analyze endpoint."""

    def test_analyze_player_success(
        self, mock_detection_service, sample_detection_response
    ):
        """Test successful player analysis."""
        # Setup mock
        mock_detection_service.analyze_player.return_value = sample_detection_response

        from app.api.dependencies import get_detection_service

        app.dependency_overrides[get_detection_service] = lambda: mock_detection_service

        with TestClient(app) as client:
            response = client.post(
                "/detection/analyze",
                json={
                    "puuid": "sample-puuid-123",
                    "min_games": 30,
                    "queue_filter": 420,
                    "force_reanalyze": False,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["puuid"] == "sample-puuid-123"
            assert data["is_smurf"] is True

            # Verify service was called with correct parameters
            mock_detection_service.analyze_player.assert_called_once()

        app.dependency_overrides.clear()

    def test_analyze_player_not_found(self, mock_detection_service):
        """Test analysis when player not found."""
        mock_detection_service.analyze_player.side_effect = ValueError(
            "Player not found"
        )

        from app.api.dependencies import get_detection_service

        app.dependency_overrides[get_detection_service] = lambda: mock_detection_service

        with TestClient(app) as client:
            response = client.post(
                "/detection/analyze",
                json={"puuid": "missing-puuid", "min_games": 30},
            )

            assert response.status_code == 404

        app.dependency_overrides.clear()


class TestDetectionHistoryEndpoint:
    """Test /detection/player/{puuid}/history endpoint."""

    def test_get_detection_history_success(
        self, mock_detection_service, sample_detection_response
    ):
        """Test successful history retrieval."""
        # Create multiple detection responses for history
        history = [sample_detection_response] * 3

        mock_detection_service.get_detection_history.return_value = history

        from app.api.dependencies import get_detection_service

        app.dependency_overrides[get_detection_service] = lambda: mock_detection_service

        with TestClient(app) as client:
            response = client.get("/detection/player/sample-puuid-123/history?limit=10")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert all(d["puuid"] == "sample-puuid-123" for d in data)

        app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
