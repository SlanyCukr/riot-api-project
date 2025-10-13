"""
Tests for match API endpoints.
"""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.api.matches import router
from app.schemas.matches import MatchResponse, MatchListResponse, MatchStatsResponse


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_match_service():
    """Mock match service."""
    service = AsyncMock()
    service.get_player_matches = AsyncMock()
    service.get_match_details = AsyncMock()
    service.get_player_stats = AsyncMock()
    service.get_player_encounters = AsyncMock()
    service.search_matches = AsyncMock()
    service.get_match_by_id_with_participants = AsyncMock()
    return service


@pytest.fixture
def mock_stats_service():
    """Mock stats service."""
    service = AsyncMock()
    service.calculate_player_statistics = AsyncMock()
    service.calculate_encounter_statistics = AsyncMock()
    service.calculate_match_statistics = AsyncMock()
    return service


@pytest.fixture
def sample_match_data():
    """Sample match data for testing."""
    return {
        "match_id": "EUN1_1234567890",
        "platform_id": "EUN1",
        "game_creation": 1710000000000,
        "game_duration": 1800,
        "queue_id": 420,
        "game_version": "14.20.555.5555",
        "map_id": 11,
        "game_mode": "CLASSIC",
        "game_type": "MATCHED_GAME",
        "created_at": "2024-03-10T12:00:00Z",
        "updated_at": "2024-03-10T12:00:00Z",
    }


@pytest.fixture
def sample_match_response(sample_match_data):
    """Sample match response."""
    return MatchResponse(**sample_match_data)


@pytest.fixture
def sample_match_list_response(sample_match_response):
    """Sample match list response."""
    return MatchListResponse(matches=[sample_match_response], total=1, start=0, count=1)


@pytest.fixture
def sample_match_stats_response():
    """Sample match stats response."""
    return MatchStatsResponse(
        puuid=str(uuid4()),
        total_matches=10,
        wins=6,
        losses=4,
        win_rate=0.6,
        avg_kills=5.2,
        avg_deaths=3.1,
        avg_assists=7.8,
        avg_kda=4.2,
        avg_cs=150.5,
        avg_vision_score=25.3,
    )


class TestMatchEndpoints:
    """Test class for match endpoints."""

    def test_get_player_matches_success(
        self, client, mock_match_service, sample_match_list_response
    ):
        """Test successful player matches retrieval."""
        # Setup mock
        mock_match_service.get_player_matches.return_value = sample_match_list_response

        # Override dependency
        app.dependency_overrides[router.get_match_service] = lambda: mock_match_service

        # Make request
        puuid = str(uuid4())
        response = client.get(f"/matches/player/{puuid}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["start"] == 0
        assert data["count"] == 1
        assert len(data["matches"]) == 1

        # Verify service call
        mock_match_service.get_player_matches.assert_called_once_with(
            puuid=puuid, start=0, count=20, queue=None, start_time=None, end_time=None
        )

    def test_get_player_matches_with_filters(
        self, client, mock_match_service, sample_match_list_response
    ):
        """Test player matches retrieval with filters."""
        # Setup mock
        mock_match_service.get_player_matches.return_value = sample_match_list_response

        # Override dependency
        app.dependency_overrides[router.get_match_service] = lambda: mock_match_service

        # Make request with filters
        puuid = str(uuid4())
        response = client.get(
            f"/matches/player/{puuid}?queue=420&start=10&count=50&start_time=1710000000000&end_time=1710086400000"
        )

        # Assertions
        assert response.status_code == 200

        # Verify service call with filters
        mock_match_service.get_player_matches.assert_called_once_with(
            puuid=puuid,
            start=10,
            count=50,
            queue=420,
            start_time=1710000000000,
            end_time=1710086400000,
        )

    def test_get_match_details_success(
        self, client, mock_match_service, sample_match_response
    ):
        """Test successful match details retrieval."""
        # Setup mock
        mock_match_service.get_match_details.return_value = sample_match_response

        # Override dependency
        app.dependency_overrides[router.get_match_service] = lambda: mock_match_service

        # Make request
        match_id = "EUN1_1234567890"
        response = client.get(f"/matches/{match_id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == match_id
        assert data["queue_id"] == 420

        # Verify service call
        mock_match_service.get_match_details.assert_called_once_with(match_id)

    def test_get_match_details_not_found(self, client, mock_match_service):
        """Test match details retrieval when match not found."""
        # Setup mock
        mock_match_service.get_match_details.return_value = None

        # Override dependency
        app.dependency_overrides[router.get_match_service] = lambda: mock_match_service

        # Make request
        match_id = "EUN1_NONEXISTENT"
        response = client.get(f"/matches/{match_id}")

        # Assertions
        assert response.status_code == 404
        assert "Match not found" in response.json()["detail"]

    def test_get_player_match_stats_success(
        self, client, mock_match_service, sample_match_stats_response
    ):
        """Test successful player match stats retrieval."""
        # Setup mock
        mock_match_service.get_player_stats.return_value = sample_match_stats_response

        # Override dependency
        app.dependency_overrides[router.get_match_service] = lambda: mock_match_service

        # Make request
        puuid = str(uuid4())
        response = client.get(f"/matches/player/{puuid}/stats")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["total_matches"] == 10
        assert data["wins"] == 6
        assert data["losses"] == 4
        assert data["win_rate"] == 0.6

        # Verify service call
        mock_match_service.get_player_stats.assert_called_once_with(
            puuid=puuid, queue=None, limit=50
        )

    def test_get_player_encounters_success(self, client, mock_match_service):
        """Test successful player encounters retrieval."""
        # Setup mock
        encounter_puuids = [str(uuid4()), str(uuid4()), str(uuid4())]
        mock_match_service.get_player_encounters.return_value = encounter_puuids

        # Override dependency
        app.dependency_overrides[router.get_match_service] = lambda: mock_match_service

        # Make request
        puuid = str(uuid4())
        response = client.get(f"/matches/player/{puuid}/encounters")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(isinstance(uuid_str, str) for uuid_str in data)

        # Verify service call
        mock_match_service.get_player_encounters.assert_called_once_with(
            puuid=puuid, limit=20
        )

    def test_search_matches_success(
        self, client, mock_match_service, sample_match_list_response
    ):
        """Test successful match search."""
        # Setup mock
        mock_match_service.search_matches.return_value = {
            "matches": [sample_match_response],
            "total": 1,
            "page": 1,
            "size": 20,
            "pages": 1,
        }

        # Override dependency
        app.dependency_overrides[router.get_match_service] = lambda: mock_match_service

        # Make request
        search_data = {"puuid": str(uuid4()), "queue_id": 420, "page": 1, "size": 20}
        response = client.post("/matches/search", json=search_data)

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["size"] == 20
        assert len(data["matches"]) == 1

        # Verify service call
        mock_match_service.search_matches.assert_called_once()

    def test_get_match_participants_success(self, client, mock_match_service):
        """Test successful match participants retrieval."""
        # Setup mock
        mock_match_service.get_match_by_id_with_participants.return_value = {
            "match": sample_match_response,
            "participants": [
                {
                    "puuid": str(uuid4()),
                    "summoner_name": "TestPlayer1",
                    "champion_name": "Ahri",
                    "kills": 5,
                    "deaths": 3,
                    "assists": 8,
                }
            ],
        }

        # Override dependency
        app.dependency_overrides[router.get_match_service] = lambda: mock_match_service

        # Make request
        match_id = "EUN1_1234567890"
        response = client.get(f"/matches/{match_id}/participants")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "match" in data
        assert "participants" in data
        assert len(data["participants"]) == 1

        # Verify service call
        mock_match_service.get_match_by_id_with_participants.assert_called_once_with(
            match_id
        )

    def test_error_handling(self, client, mock_match_service):
        """Test error handling in match endpoints."""
        # Setup mock to raise exception
        mock_match_service.get_player_matches.side_effect = Exception("Database error")

        # Override dependency
        app.dependency_overrides[router.get_match_service] = lambda: mock_match_service

        # Make request
        puuid = str(uuid4())
        response = client.get(f"/matches/player/{puuid}")

        # Assertions
        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]

    def test_validation_error_handling(self, client):
        """Test validation error handling."""
        # Make request with invalid count parameter
        puuid = str(uuid4())
        response = client.get(f"/matches/player/{puuid}?count=0")

        # Assertions
        assert response.status_code == 422  # Validation error

    def test_get_player_stats_returns_aggregate_statistics(
        self, client, mock_match_service
    ):
        """Test player stats endpoint returns correct aggregates."""
        # Setup mock
        mock_match_service.get_player_stats.return_value = MatchStatsResponse(
            puuid=str(uuid4()),
            total_matches=50,
            wins=32,
            losses=18,
            win_rate=0.64,
            avg_kills=7.5,
            avg_deaths=4.2,
            avg_assists=9.3,
            avg_kda=4.0,
            avg_cs=195.5,
            avg_vision_score=28.7,
        )

        # Override dependency
        app.dependency_overrides[router.get_match_service] = lambda: mock_match_service

        # Make request
        puuid = str(uuid4())
        response = client.get(f"/matches/player/{puuid}/stats")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["total_matches"] == 50
        assert data["wins"] == 32
        assert data["losses"] == 18
        assert data["win_rate"] == 0.64
        assert data["avg_kda"] == 4.0
        assert data["avg_cs"] == 195.5

        # Verify service call
        mock_match_service.get_player_stats.assert_called_once()

    def test_get_player_stats_handles_no_matches(self, client, mock_match_service):
        """Test player stats with player who has no matches."""
        # Setup mock with zero stats
        mock_match_service.get_player_stats.return_value = MatchStatsResponse(
            puuid=str(uuid4()),
            total_matches=0,
            wins=0,
            losses=0,
            win_rate=0.0,
            avg_kills=0.0,
            avg_deaths=0.0,
            avg_assists=0.0,
            avg_kda=0.0,
            avg_cs=0.0,
            avg_vision_score=0.0,
        )

        # Override dependency
        app.dependency_overrides[router.get_match_service] = lambda: mock_match_service

        # Make request
        puuid = str(uuid4())
        response = client.get(f"/matches/player/{puuid}/stats")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["total_matches"] == 0
        assert data["win_rate"] == 0.0

    def tearDown(self):
        """Clean up after tests."""
        app.dependency_overrides.clear()
