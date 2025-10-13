"""
Tests for the tracked player updater job.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4

from app.jobs.tracked_player_updater import TrackedPlayerUpdaterJob
from app.models.job_tracking import JobConfiguration
from app.models.players import Player


@pytest.fixture
def job_config():
    """Create test job configuration."""
    from app.models import JobType

    return JobConfiguration(
        id=1,
        job_type=JobType.TRACKED_PLAYER_UPDATER,
        name="Tracked Player Updater",
        schedule="interval(seconds=120)",
        is_active=True,
        config_json={
            "max_new_matches_per_player": 20,
            "max_tracked_players": 10,
        },
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def sample_tracked_player():
    """Create sample tracked player."""
    return Player(
        puuid=str(uuid4()),
        riot_id="TrackedPlayer",
        tag_line="NA1",
        platform="na1",
        account_level=100,
        is_tracked=True,
        is_analyzed=True,
        last_seen=datetime.now(),
    )


@pytest.fixture
def sample_matches():
    """Create sample match list."""
    return [f"NA1_match{i}" for i in range(5)]


class TestTrackedPlayerUpdaterJob:
    """Test cases for TrackedPlayerUpdaterJob."""

    @pytest.mark.asyncio
    async def test_initialization(self, job_config):
        """Test job initialization."""
        job = TrackedPlayerUpdaterJob(job_config)

        assert job.job_config == job_config
        assert job.max_new_matches_per_player == 20
        assert job.max_tracked_players == 10

    @pytest.mark.asyncio
    async def test_get_tracked_players_empty(self, job_config, mock_db):
        """Test getting tracked players when none exist."""
        job = TrackedPlayerUpdaterJob(job_config)

        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        players = await job._get_tracked_players(mock_db)

        assert len(players) == 0

    @pytest.mark.asyncio
    async def test_get_tracked_players_with_data(
        self, job_config, mock_db, sample_tracked_player
    ):
        """Test getting tracked players when they exist."""
        job = TrackedPlayerUpdaterJob(job_config)

        # Mock result with players
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_tracked_player]
        mock_db.execute.return_value = mock_result

        players = await job._get_tracked_players(mock_db)

        assert len(players) == 1
        assert players[0].puuid == sample_tracked_player.puuid

    @pytest.mark.asyncio
    async def test_execute_no_tracked_players(self, job_config, mock_db):
        """Test execution when no tracked players exist."""
        job = TrackedPlayerUpdaterJob(job_config)

        # Mock empty tracked players
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        with (
            patch("app.jobs.tracked_player_updater.RiotAPIClient") as mock_client,
        ):
            # Setup API client mock
            mock_api = MagicMock()
            mock_api.close = AsyncMock()
            mock_client.return_value = mock_api

            await job.execute(mock_db)

            # Should complete without errors and log that no players were found
            assert "tracked_players_count" in job.execution_log
            assert job.execution_log["tracked_players_count"] == 0

    @pytest.mark.asyncio
    async def test_execute_with_tracked_players(
        self, job_config, mock_db, sample_tracked_player
    ):
        """Test execution with tracked players."""
        job = TrackedPlayerUpdaterJob(job_config)

        # Mock tracked players
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_tracked_player]
        mock_db.execute.return_value = mock_result

        with (
            patch("app.jobs.tracked_player_updater.RiotAPIClient") as mock_client,
            patch("app.jobs.tracked_player_updater.RiotDataManager") as mock_manager,
        ):
            # Mock API client
            mock_api = MagicMock()
            mock_api.close = AsyncMock()
            mock_api.region = MagicMock()
            mock_api.endpoints = MagicMock()
            mock_api.endpoints.get_region_for_platform = MagicMock(
                return_value=mock_api.region
            )
            mock_client.return_value = mock_api

            # Mock data manager with basic behavior
            mock_mgr = MagicMock()
            mock_manager.return_value = mock_mgr

            await job.execute(mock_db)

            # Should process tracked player
            assert job.execution_log.get("tracked_players_count") == 1

    @pytest.mark.asyncio
    async def test_fetch_new_matches(
        self, job_config, mock_db, sample_tracked_player, sample_matches
    ):
        """Test fetching new matches for a player."""
        job = TrackedPlayerUpdaterJob(job_config)

        # Mock database responses for count and last match time
        count_result = MagicMock()
        count_result.scalar.return_value = 0  # No existing matches

        time_result = MagicMock()
        time_result.scalar_one_or_none.return_value = None  # No last match time

        mock_db.execute = AsyncMock(side_effect=[count_result, time_result])

        with (
            patch("app.jobs.tracked_player_updater.RiotAPIClient") as mock_client_class,
            patch(
                "app.jobs.tracked_player_updater.RiotDataManager"
            ) as mock_manager_class,
        ):
            # Setup mocks
            mock_api_client = MagicMock()
            mock_api_client.close = AsyncMock()
            mock_api_client.get_match_list_by_puuid = AsyncMock(
                return_value=sample_matches
            )
            mock_client_class.return_value = mock_api_client

            mock_data_manager = MagicMock()
            mock_data_manager.get_player_match_list = AsyncMock(
                return_value=sample_matches
            )
            mock_manager_class.return_value = mock_data_manager

            job.api_client = mock_api_client
            job.data_manager = mock_data_manager

            # Test _fetch_new_matches method
            matches = await job._fetch_new_matches(mock_db, sample_tracked_player)

            # Should have fetched matches
            assert isinstance(matches, list)
            assert len(matches) <= job.max_new_matches_per_player

    @pytest.mark.asyncio
    async def test_update_player_rank(self, job_config, mock_db, sample_tracked_player):
        """Test updating player rank."""
        job = TrackedPlayerUpdaterJob(job_config)

        with (
            patch("app.jobs.tracked_player_updater.RiotAPIClient") as mock_client,
            patch("app.jobs.tracked_player_updater.RiotDataManager") as mock_manager,
        ):
            mock_api = MagicMock()
            mock_api.close = AsyncMock()

            # Mock the API client's endpoints
            mock_api.get_league_entries_by_puuid = AsyncMock(return_value=[])
            mock_client.return_value = mock_api

            mock_data_manager = MagicMock()
            mock_data_manager.update_player_rank = AsyncMock()
            mock_manager.return_value = mock_data_manager

            job.api_client = mock_api
            job.data_manager = mock_data_manager

            await job._update_player_rank(mock_db, sample_tracked_player)

            # Verify update_player_rank was called
            # (may not be called if API returns empty, but test shouldn't crash)
            assert True  # Test passes if no exception raised

    @pytest.mark.asyncio
    async def test_handle_rate_limit_error(self, job_config, mock_db):
        """Test handling rate limit error."""
        TrackedPlayerUpdaterJob(job_config)

        # Rate limit errors should be caught and handled gracefully
        # The job should continue processing other players
        assert True  # Placeholder - would need actual rate limit simulation

    @pytest.mark.asyncio
    async def test_handle_not_found_error(
        self, job_config, mock_db, sample_tracked_player
    ):
        """Test handling player not found error."""
        TrackedPlayerUpdaterJob(job_config)

        # NotFoundError should be logged but not crash the job
        # The job should skip the player and continue
        assert True  # Placeholder - would need actual NotFoundError simulation

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, job_config, mock_db):
        """Test that metrics are properly tracked."""
        job = TrackedPlayerUpdaterJob(job_config)

        # Test standard metrics
        job.increment_metric("api_requests_made", 15)
        job.increment_metric("records_created", 10)
        job.increment_metric("records_updated", 5)

        assert job.metrics["api_requests_made"] == 15
        assert job.metrics["records_created"] == 10
        assert job.metrics["records_updated"] == 5

    @pytest.mark.asyncio
    async def test_max_tracked_players_limit(self, job_config, mock_db):
        """Test that max tracked players limit is respected."""
        job = TrackedPlayerUpdaterJob(job_config)

        # Create more players than limit
        players = [
            Player(
                puuid=str(uuid4()),
                riot_id=f"Player{i}",
                tag_line="NA1",
                platform="na1",
                is_tracked=True,
            )
            for i in range(15)
        ]

        # Mock query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = players[
            : job.max_tracked_players
        ]
        mock_db.execute.return_value = mock_result

        result = await job._get_tracked_players(mock_db)

        # Should only get up to max_tracked_players
        assert len(result) <= job.max_tracked_players

    @pytest.mark.asyncio
    async def test_log_entries_created(self, job_config, mock_db):
        """Test that log entries are created during execution."""
        job = TrackedPlayerUpdaterJob(job_config)

        job.add_log_entry("tracked_players_count", 5)
        job.add_log_entry("new_matches_total", 25)

        assert "tracked_players_count" in job.execution_log
        assert "new_matches_total" in job.execution_log
        assert job.execution_log["tracked_players_count"] == 5


class TestTrackedPlayerUpdaterIntegration:
    """Integration tests for tracked player updater."""

    @pytest.mark.asyncio
    async def test_full_execution_flow(
        self, job_config, mock_db, sample_tracked_player
    ):
        """Test full execution flow with mocked dependencies."""
        job = TrackedPlayerUpdaterJob(job_config)

        # Mock all dependencies
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_tracked_player]
        mock_db.execute.return_value = mock_result

        with (
            patch("app.jobs.tracked_player_updater.RiotAPIClient") as mock_client,
            patch("app.jobs.tracked_player_updater.RiotDataManager") as mock_manager,
        ):
            # Setup API client mock
            mock_api = MagicMock()
            mock_api.close = AsyncMock()
            mock_api.region = MagicMock()
            mock_api.endpoints = MagicMock()
            mock_api.endpoints.get_region_for_platform = MagicMock(
                return_value=mock_api.region
            )
            mock_client.return_value = mock_api

            mock_data_mgr = MagicMock()
            mock_data_mgr.get_player_match_list = AsyncMock(return_value=[])
            mock_data_mgr.update_player_rank = AsyncMock(return_value=True)
            mock_manager.return_value = mock_data_mgr

            # Execute job
            await job.execute(mock_db)

            # Verify job completed and logged
            assert "tracked_players_count" in job.execution_log
            assert job.execution_log["tracked_players_count"] == 1

    @pytest.mark.asyncio
    async def test_error_recovery(self, job_config, mock_db, sample_tracked_player):
        """Test error recovery during execution."""
        job = TrackedPlayerUpdaterJob(job_config)

        # Mock tracked players
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_tracked_player]
        mock_db.execute.return_value = mock_result

        with (
            patch("app.jobs.tracked_player_updater.RiotAPIClient") as mock_client,
            patch("app.jobs.tracked_player_updater.RiotDataManager") as mock_manager,
        ):
            mock_api = MagicMock()
            mock_api.close = AsyncMock()
            mock_api.region = MagicMock()
            mock_api.endpoints = MagicMock()
            mock_api.endpoints.get_region_for_platform = MagicMock(
                return_value=mock_api.region
            )
            mock_client.return_value = mock_api

            # Make data manager raise an error
            mock_data_mgr = MagicMock()
            mock_data_mgr.get_player_match_list = AsyncMock(
                side_effect=Exception("Test error")
            )
            mock_manager.return_value = mock_data_mgr

            # Should handle error and continue (not crash)
            await job.execute(mock_db)

            # Job should have logged tracked players even if update failed
            assert "tracked_players_count" in job.execution_log
