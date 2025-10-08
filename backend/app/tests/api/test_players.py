"""
Test cases for the player API endpoints.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.players import PlayerResponse
from app.models.players import Player


@pytest.fixture
def mock_player_service():
    """Mock player service for testing."""
    service = AsyncMock()
    return service


@pytest.fixture
def sample_player_response():
    """Sample player response for testing."""
    return PlayerResponse(
        puuid="sample-puuid-123",
        riot_id="TestPlayer#EUW",
        tag_line="EUW",
        summoner_name="TestPlayer",
        platform="eun1",
        account_level=100,
        id=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_seen=datetime.utcnow(),
    )


@pytest.fixture
def sample_player_db():
    """Sample player database model for testing."""
    return Player(
        puuid="sample-puuid-123",
        riot_id="TestPlayer",
        tag_line="EUW",
        summoner_name="TestPlayer",
        platform="eun1",
        account_level=100,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_seen=datetime.utcnow(),
    )


class TestPlayerAPI:
    """Test class for player API endpoints."""

    def test_search_player_by_riot_id_success(
        self, mock_player_service, sample_player_response
    ):
        """Test successful player search by Riot ID."""
        # Setup mock
        mock_player_service.get_player_by_riot_id.return_value = sample_player_response

        # Create test client with dependency override
        from app.api.dependencies import get_player_service

        app.dependency_overrides[get_player_service] = lambda: mock_player_service

        with TestClient(app) as client:
            response = client.get(
                "/players/search?riot_id=TestPlayer#EUW&platform=eun1"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["puuid"] == "sample-puuid-123"
            assert data["riot_id"] == "TestPlayer#EUW"
            assert data["summoner_name"] == "TestPlayer"

            # Verify service was called correctly
            mock_player_service.get_player_by_riot_id.assert_called_once_with(
                "TestPlayer", "EUW", "eun1"
            )

        # Clean up
        app.dependency_overrides.clear()

    def test_search_player_by_summoner_name_success(
        self, mock_player_service, sample_player_response
    ):
        """Test successful player search by summoner name."""
        # Setup mock
        mock_player_service.get_player_by_summoner_name.return_value = (
            sample_player_response
        )

        # Create test client with dependency override
        from app.api.dependencies import get_player_service

        app.dependency_overrides[get_player_service] = lambda: mock_player_service

        with TestClient(app) as client:
            response = client.get(
                "/players/search?summoner_name=TestPlayer&platform=eun1"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["puuid"] == "sample-puuid-123"
            assert data["summoner_name"] == "TestPlayer"

            # Verify service was called correctly
            mock_player_service.get_player_by_summoner_name.assert_called_once_with(
                "TestPlayer", "eun1"
            )

        # Clean up
        app.dependency_overrides.clear()

    def test_search_player_missing_parameters(self):
        """Test player search with missing parameters."""
        with TestClient(app) as client:
            response = client.get("/players/search")

            assert response.status_code == 400
            data = response.json()
            assert "Either riot_id or summoner_name must be provided" in data["detail"]

    def test_search_player_invalid_riot_id_format(self):
        """Test player search with invalid Riot ID format."""
        with TestClient(app) as client:
            response = client.get("/players/search?riot_id=InvalidFormat")

            assert response.status_code == 400
            data = response.json()
            assert "Riot ID must be in format name#tag" in data["detail"]

    def test_search_player_not_found(self, mock_player_service):
        """Test player search when player is not found."""
        # Setup mock to raise exception
        mock_player_service.get_player_by_riot_id.side_effect = Exception(
            "Player not found"
        )

        # Create test client with dependency override
        from app.api.dependencies import get_player_service

        app.dependency_overrides[get_player_service] = lambda: mock_player_service

        with TestClient(app) as client:
            response = client.get("/players/search?riot_id=MissingPlayer#EUW")

            assert response.status_code == 404
            data = response.json()
            assert "Player not found" in data["detail"]

        # Clean up
        app.dependency_overrides.clear()

    def test_get_player_by_puuid_success(
        self, mock_player_service, sample_player_response
    ):
        """Test successful get player by PUUID."""
        # Setup mock
        mock_player_service.get_player_by_puuid.return_value = sample_player_response

        # Create test client with dependency override
        from app.api.dependencies import get_player_service

        app.dependency_overrides[get_player_service] = lambda: mock_player_service

        with TestClient(app) as client:
            response = client.get(f"/players/{sample_player_response.puuid}")

            assert response.status_code == 200
            data = response.json()
            assert data["puuid"] == sample_player_response.puuid

            # Verify service was called correctly
            mock_player_service.get_player_by_puuid.assert_called_once_with(
                sample_player_response.puuid
            )

        # Clean up
        app.dependency_overrides.clear()

    def test_get_player_by_puuid_not_found(self, mock_player_service):
        """Test get player by PUUID when player is not found."""
        # Setup mock
        mock_player_service.get_player_by_puuid.return_value = None

        # Create test client with dependency override
        from app.api.dependencies import get_player_service

        app.dependency_overrides[get_player_service] = lambda: mock_player_service

        with TestClient(app) as client:
            response = client.get("/players/nonexistent-puuid")

            assert response.status_code == 404
            data = response.json()
            assert "Player not found" in data["detail"]

        # Clean up
        app.dependency_overrides.clear()

    def test_get_player_recent_opponents(self, mock_player_service):
        """Test get player recent opponents."""
        # Setup mock
        mock_player_service.get_recent_opponents.return_value = [
            "opponent1",
            "opponent2",
        ]

        # Create test client with dependency override
        from app.api.dependencies import get_player_service

        app.dependency_overrides[get_player_service] = lambda: mock_player_service

        with TestClient(app) as client:
            response = client.get("/players/sample-puuid/recent?limit=10")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0] == "opponent1"

            # Verify service was called correctly
            mock_player_service.get_recent_opponents.assert_called_once_with(
                "sample-puuid", 10
            )

        # Clean up
        app.dependency_overrides.clear()

    def test_get_players_with_platform_filter(
        self, mock_player_service, sample_player_response
    ):
        """Test get players with platform filter."""
        # Setup mock
        mock_player_service.search_players.return_value = [sample_player_response]

        # Create test client with dependency override
        from app.api.dependencies import get_player_service

        app.dependency_overrides[get_player_service] = lambda: mock_player_service

        with TestClient(app) as client:
            response = client.get("/players?platform=eun1&limit=20")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["platform"] == "eun1"

            # Verify service was called correctly
            mock_player_service.search_players.assert_called_once_with(
                platform="eun1", limit=20
            )

        # Clean up
        app.dependency_overrides.clear()

    def test_search_players_advanced(self, mock_player_service, sample_player_response):
        """Test advanced player search."""
        # Setup mock
        mock_player_service.search_players.return_value = [sample_player_response]

        # Create test client with dependency override
        from app.api.dependencies import get_player_service

        app.dependency_overrides[get_player_service] = lambda: mock_player_service

        search_data = {"riot_id": "TestPlayer#EUW", "platform": "eun1", "size": 10}

        with TestClient(app) as client:
            response = client.post("/players/search", json=search_data)

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["riot_id"] == "TestPlayer#EUW"

            # Verify service was called correctly
            mock_player_service.search_players.assert_called_once_with(
                summoner_name=None, riot_id="TestPlayer#EUW", platform="eun1", limit=10
            )

        # Clean up
        app.dependency_overrides.clear()

    def test_bulk_get_players(self, mock_player_service, sample_player_response):
        """Test bulk get players."""
        # Setup mock
        mock_player_service.bulk_get_players.return_value = [sample_player_response]

        # Create test client with dependency override
        from app.api.dependencies import get_player_service

        app.dependency_overrides[get_player_service] = lambda: mock_player_service

        bulk_data = {"puuids": [sample_player_response.puuid]}

        with TestClient(app) as client:
            response = client.post("/players/bulk", json=bulk_data)

            assert response.status_code == 200
            data = response.json()
            assert "players" in data
            assert "not_found" in data
            assert len(data["players"]) == 1
            assert len(data["not_found"]) == 0

            # Verify service was called correctly
            mock_player_service.bulk_get_players.assert_called_once_with(
                [sample_player_response.puuid]
            )

        # Clean up
        app.dependency_overrides.clear()
