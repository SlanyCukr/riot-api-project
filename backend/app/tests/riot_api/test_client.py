"""
Tests for Riot API client.
"""

import pytest
import pytest_asyncio
import aiohttp
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.app.riot_api.client import RiotAPIClient
from backend.app.riot_api.errors import AuthenticationError, NotFoundError
from backend.app.riot_api.models import AccountDTO, SummonerDTO, MatchListDTO, MatchDTO
from backend.app.riot_api.endpoints import Region, Platform, QueueType


@pytest_asyncio.fixture
async def client():
    """Create a test client instance."""
    client = RiotAPIClient(
        api_key="test_api_key",
        region=Region.EUROPE,
        platform=Platform.EUN1,
        enable_logging=False,
    )
    yield client
    await client.close()


@pytest_asyncio.fixture
async def mock_session():
    """Create a mock aiohttp session."""
    session = Mock(spec=aiohttp.ClientSession)
    session.request = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def sample_account_data():
    """Sample account data for testing."""
    return {"puuid": "test-puuid-123", "gameName": "TestPlayer", "tagLine": "EUW"}


@pytest.fixture
def sample_summoner_data():
    """Sample summoner data for testing."""
    return {
        "id": "test-summoner-id",
        "puuid": "test-puuid-123",
        "name": "TestPlayer",
        "profileIconId": 1234,
        "summonerLevel": 100,
        "revisionDate": 1234567890000,
    }


@pytest.fixture
def sample_match_list_data():
    """Sample match list data for testing."""
    return ["EUW1_1234567890", "EUW1_1234567891", "EUW1_1234567892"]


@pytest.fixture
def sample_match_data():
    """Sample match data for testing."""
    return {
        "metadata": {
            "matchId": "EUW1_1234567890",
            "dataVersion": "14.20.555.5555",
            "participants": ["puuid1", "puuid2", "puuid3", "puuid4", "puuid5"],
        },
        "info": {
            "gameCreation": 1710000000000,
            "gameDuration": 1800,
            "gameStartTimestamp": 1710000000000,
            "queueId": 420,
            "mapId": 11,
            "gameVersion": "14.20.555.5555",
            "gameMode": "CLASSIC",
            "gameType": "MATCHED_GAME",
            "participants": [
                {
                    "puuid": "puuid1",
                    "summonerName": "Player1",
                    "summonerId": "summoner1",
                    "teamId": 100,
                    "win": True,
                    "championId": 238,
                    "championName": "Zed",
                    "kills": 12,
                    "deaths": 2,
                    "assists": 6,
                    "champLevel": 18,
                    "visionScore": 25.0,
                    "goldEarned": 15000,
                    "totalMinionsKilled": 200,
                    "neutralMinionsKilled": 50,
                    "role": "MIDDLE",
                    "lane": "MID",
                    "individualPosition": "MIDDLE",
                    "teamPosition": "MIDDLE",
                    "challenges": {"kda": 9.0},
                    "perks": {"styles": []},
                }
            ],
            "teams": [
                {"teamId": 100, "win": True, "bans": [], "objectives": {}},
                {"teamId": 200, "win": False, "bans": [], "objectives": {}},
            ],
            "platformId": "EUW1",
        },
    }


class TestRiotAPIClient:
    """Test cases for RiotAPIClient."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, client):
        """Test client initialization."""
        assert client.api_key == "test_api_key"
        assert client.region == Region.EUROPE
        assert client.platform == Platform.EUN1
        assert client.enable_logging is False
        assert client.rate_limiter is not None
        assert client.endpoints is not None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with RiotAPIClient(api_key="test_key") as client:
            assert client.session is not None
            assert not client.session.closed
        assert client.session.closed

    @pytest.mark.asyncio
    async def test_get_account_by_riot_id(self, client, sample_account_data):
        """Test getting account by Riot ID."""
        # Mock the HTTP request
        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = sample_account_data

            result = await client.get_account_by_riot_id("TestPlayer", "EUW")

            # Verify the result
            assert isinstance(result, AccountDTO)
            assert result.puuid == "test-puuid-123"
            assert result.game_name == "TestPlayer"
            assert result.tag_line == "EUW"

            # Verify the request was made correctly
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_summoner_by_puuid(self, client, sample_summoner_data):
        """Test getting summoner by PUUID."""
        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = sample_summoner_data

            result = await client.get_summoner_by_puuid("test-puuid-123")

            # Verify the result
            assert isinstance(result, SummonerDTO)
            assert result.id == "test-summoner-id"
            assert result.puuid == "test-puuid-123"
            assert result.name == "TestPlayer"
            assert result.summoner_level == 100

            # Verify revision date parsing
            assert result.revision_date is not None
            assert isinstance(result.revision_date, datetime)

            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_match_list_by_puuid(self, client, sample_match_list_data):
        """Test getting match list by PUUID."""
        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = sample_match_list_data

            result = await client.get_match_list_by_puuid(
                "test-puuid-123", start=0, count=20, queue=QueueType.RANKED_SOLO
            )

            # Verify the result
            assert isinstance(result, MatchListDTO)
            assert len(result.match_ids) == 3
            assert result.start == 0
            assert result.count == 20
            assert result.match_ids[0] == "EUW1_1234567890"

            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_match(self, client, sample_match_data):
        """Test getting match details."""
        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = sample_match_data

            result = await client.get_match("EUW1_1234567890")

            # Verify the result
            assert isinstance(result, MatchDTO)
            assert result.match_id == "EUW1_1234567890"
            assert result.info.queue_id == 420
            assert len(result.info.participants) == 1
            assert result.info.participants[0].puuid == "puuid1"
            assert result.info.participants[0].win is True

            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_puuid_by_riot_id(self, client, sample_account_data):
        """Test getting PUUID by Riot ID."""
        with patch.object(
            client, "get_account_by_riot_id", new_callable=AsyncMock
        ) as mock_get_account:
            mock_account = AccountDTO(**sample_account_data)
            mock_get_account.return_value = mock_account

            result = await client.get_puuid_by_riot_id("TestPlayer", "EUW")

            assert result == "test-puuid-123"
            mock_get_account.assert_called_once_with("TestPlayer", "EUW", None)

    @pytest.mark.asyncio
    async def test_get_puuid_by_summoner_name(self, client, sample_summoner_data):
        """Test getting PUUID by summoner name."""
        with patch.object(
            client, "get_summoner_by_name", new_callable=AsyncMock
        ) as mock_get_summoner:
            mock_summoner = SummonerDTO(**sample_summoner_data)
            mock_get_summoner.return_value = mock_summoner

            result = await client.get_puuid_by_summoner_name("TestPlayer")

            assert result == "test-puuid-123"
            mock_get_summoner.assert_called_once_with("TestPlayer", None)

    @pytest.mark.asyncio
    async def test_get_match_history_stats(
        self, client, sample_match_list_data, sample_match_data
    ):
        """Test getting match history statistics."""
        with (
            patch.object(
                client, "get_match_list_by_puuid", new_callable=AsyncMock
            ) as mock_get_list,
            patch.object(client, "get_match", new_callable=AsyncMock) as mock_get_match,
        ):
            mock_get_list.return_value = MatchListDTO(
                match_ids=sample_match_list_data, start=0, count=3
            )
            mock_get_match.return_value = MatchDTO(**sample_match_data)

            result = await client.get_match_history_stats(
                "test-puuid-123", queue=QueueType.RANKED_SOLO, max_matches=3
            )

            # Verify statistics
            assert result["puuid"] == "test-puuid-123"
            assert result["queue"] == "420"
            assert result["total_matches"] == 3
            assert result["wins"] == 3
            assert result["win_rate"] == 100.0
            assert result["avg_kills"] == 12.0
            assert result["avg_deaths"] == 2.0
            assert result["avg_assists"] == 6.0
            assert result["kda"] == 9.0

    @pytest.mark.asyncio
    async def test_make_request_success(self, client):
        """Test successful API request."""
        with (
            patch.object(client, "start_session", new_callable=AsyncMock),
            patch.object(client, "session") as mock_session,
        ):
            mock_session.closed = False

            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"test": "data"})
            mock_response.headers = {}
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session.request.return_value = mock_response

            result = await client._make_request("https://test.com/api")

            assert result == {"test": "data"}
            assert client.stats["requests_made"] == 1

    @pytest.mark.asyncio
    async def test_make_request_401_error(self, client):
        """Test 401 authentication error."""
        with (
            patch.object(client, "start_session", new_callable=AsyncMock),
            patch.object(client, "session") as mock_session,
        ):
            mock_session.closed = False

            mock_response = AsyncMock()
            mock_response.status = 401
            mock_response.headers = {}
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session.request.return_value = mock_response

            with pytest.raises(AuthenticationError):
                await client._make_request("https://test.com/api")

            assert client.stats["errors"] == 1

    @pytest.mark.asyncio
    async def test_make_request_404_error(self, client):
        """Test 404 not found error."""
        with (
            patch.object(client, "start_session", new_callable=AsyncMock),
            patch.object(client, "session") as mock_session,
        ):
            mock_session.closed = False

            mock_response = AsyncMock()
            mock_response.status = 404
            mock_response.headers = {}
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session.request.return_value = mock_response

            with pytest.raises(NotFoundError):
                await client._make_request("https://test.com/api")

            assert client.stats["errors"] == 1

    @pytest.mark.asyncio
    async def test_make_request_429_retry(self, client):
        """Test 429 rate limit with retry."""
        with (
            patch.object(client, "start_session", new_callable=AsyncMock),
            patch.object(client, "session") as mock_session,
            patch.object(
                client.rate_limiter, "handle_429", new_callable=AsyncMock
            ) as mock_handle_429,
            patch.object(
                client.rate_limiter, "calculate_backoff", new_callable=AsyncMock
            ) as mock_backoff,
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_session.closed = False
            # First response: 429
            mock_response_429 = AsyncMock()
            mock_response_429.status = 429
            mock_response_429.headers = {"Retry-After": "1"}
            mock_response_429.__aenter__ = AsyncMock(return_value=mock_response_429)
            mock_response_429.__aexit__ = AsyncMock(return_value=None)

            # Second response: 200
            mock_response_200 = AsyncMock()
            mock_response_200.status = 200
            mock_response_200.json = AsyncMock(return_value={"success": True})
            mock_response_200.headers = {}
            mock_response_200.__aenter__ = AsyncMock(return_value=mock_response_200)
            mock_response_200.__aexit__ = AsyncMock(return_value=None)

            mock_session.request.side_effect = [mock_response_429, mock_response_200]
            mock_handle_429.return_value = 1.0
            mock_backoff.return_value = 0.1

            result = await client._make_request("https://test.com/api")

            assert result == {"success": True}
            assert client.stats["requests_made"] == 2
            assert client.stats["retries"] == 1
            mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stats(self, client):
        """Test getting client statistics."""
        stats = client.get_stats()

        assert "client" in stats
        assert "rate_limiter" in stats
        assert "region" in stats
        assert "platform" in stats

        assert stats["region"] == "europe"
        assert stats["platform"] == "eun1"

    @pytest.mark.asyncio
    async def test_reset_rate_limiter(self, client):
        """Test resetting rate limiter."""
        with patch.object(
            client.rate_limiter, "reset", new_callable=AsyncMock
        ) as mock_reset:
            await client.reset_rate_limiter()
            mock_reset.assert_called_once()

    @pytest.mark.asyncio
    async def test_active_game_not_found(self, client):
        """Test active game when player is not in game."""
        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = NotFoundError("Not found")

            result = await client.get_active_game("test-summoner-id")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_featured_games(self, client):
        """Test getting featured games."""
        sample_data = {"gameList": [], "clientRefreshInterval": 300}

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = sample_data

            result = await client.get_featured_games()

            assert result.game_list == []
            assert result.client_refresh_interval == 300

    def test_extract_endpoint_path(self, client):
        """Test endpoint path extraction."""
        path1 = client._extract_endpoint_path(
            "https://europe.api.riotgames.com/lol/match/v5/matches/EUW1_123"
        )
        path2 = client._extract_endpoint_path(
            "https://eun1.api.riotgames.com/lol/summoner/v4/summoners/by-name/test"
        )

        assert path1 == "lol/match/v5/matches/EUW1_123"
        assert path2 == "lol/summoner/v4/summoners/by-name/test"
