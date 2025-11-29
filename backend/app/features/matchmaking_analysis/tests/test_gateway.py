import pytest
from unittest.mock import AsyncMock, MagicMock
from ..gateway import MatchmakingGateway
from app.core.riot_api import RiotAPIClient
from app.core.riot_api.data_manager import RiotDataManager


@pytest.fixture
def mock_riot_client():
    return AsyncMock(spec=RiotAPIClient)


@pytest.fixture
def mock_data_manager():
    return AsyncMock(spec=RiotDataManager)


@pytest.fixture
def gateway(mock_riot_client, mock_data_manager):
    return MatchmakingGateway(mock_riot_client, mock_data_manager)


async def test_fetch_match_data(gateway, mock_riot_client, mock_data_manager):
    """Test fetching match data through gateway"""
    # Setup
    match_id = "NA1_1234567890"
    expected_dict_data = {"matchId": match_id, "gameDuration": 1800}

    # Mock MatchDTO with model_dump method
    mock_match_dto = MagicMock()
    mock_match_dto.model_dump.return_value = expected_dict_data
    mock_data_manager.get_match.return_value = mock_match_dto

    # Execute
    result = await gateway.fetch_match_data(match_id)

    # Verify
    assert result == expected_dict_data
    mock_data_manager.get_match.assert_called_once_with(match_id)
    mock_match_dto.model_dump.assert_called_once_with(by_alias=True)


async def test_get_player_recent_matches(gateway, mock_riot_client):
    """Test getting player's recent matches"""
    # Setup
    puuid = "test-puuid-123"
    match_count = 20
    expected_matches = [{"matchId": "NA1_1"}, {"matchId": "NA1_2"}]

    # Mock the match list DTO returned by riot client
    mock_match_list = MagicMock()
    mock_match_list.match_ids = ["NA1_1", "NA1_2"]
    mock_riot_client.get_match_list_by_puuid.return_value = mock_match_list

    # Execute
    result = await gateway.get_player_recent_matches(puuid, match_count)

    # Verify
    assert result == expected_matches
    mock_riot_client.get_match_list_by_puuid.assert_called_once()
