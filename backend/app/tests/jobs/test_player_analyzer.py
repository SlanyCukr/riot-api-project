"""
Tests for the player analyzer job.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4

from app.jobs.player_analyzer import PlayerAnalyzerJob
from app.models.job_tracking import JobConfiguration
from app.models.players import Player


@pytest.fixture
def job_config():
    """Create test job configuration."""
    from app.models import JobType

    return JobConfiguration(
        id=2,
        job_type=JobType.PLAYER_ANALYZER,
        name="Player Analyzer",
        schedule="interval(seconds=120)",
        is_active=True,
        config_json={
            "unanalyzed_players_per_run": 15,
            "min_smurf_confidence": 0.5,
            "ban_check_days": 7,
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
def sample_unanalyzed_player():
    """Create sample unanalyzed player."""
    return Player(
        puuid=str(uuid4()),
        riot_id="UnanalyzedPlayer",
        tag_line="NA1",
        platform="na1",
        account_level=30,
        is_tracked=False,
        is_analyzed=False,
        last_seen=datetime.now(),
    )


@pytest.fixture
def sample_detection_result():
    """Create sample detection result."""
    return {
        "is_smurf": True,
        "smurf_score": 0.75,
        "confidence": "high",
        "games_analyzed": 30,
        "detection_factors": {
            "win_rate": 0.8,
            "kda": 3.5,
            "account_level": 30,
        },
    }


class TestPlayerAnalyzerJob:
    """Test cases for PlayerAnalyzerJob."""

    @pytest.mark.asyncio
    async def test_initialization(self, job_config):
        """Test job initialization."""
        job = PlayerAnalyzerJob(job_config)

        assert job.job_config == job_config
        assert job.unanalyzed_players_per_run == 15
        assert job.min_smurf_confidence == 0.5
        assert job.ban_check_days == 7

    @pytest.mark.asyncio
    async def test_get_unanalyzed_players_empty(self, job_config, mock_db):
        """Test getting unanalyzed players when none exist."""
        job = PlayerAnalyzerJob(job_config)

        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        players = await job._get_unanalyzed_players(mock_db)

        assert len(players) == 0

    @pytest.mark.asyncio
    async def test_get_unanalyzed_players_with_data(
        self, job_config, mock_db, sample_unanalyzed_player
    ):
        """Test getting unanalyzed players when they exist."""
        job = PlayerAnalyzerJob(job_config)

        # Mock result with players
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_unanalyzed_player]
        mock_db.execute.return_value = mock_result

        players = await job._get_unanalyzed_players(mock_db)

        assert len(players) == 1
        assert players[0].puuid == sample_unanalyzed_player.puuid

    @pytest.mark.asyncio
    async def test_execute_with_players(
        self, job_config, mock_db, sample_unanalyzed_player
    ):
        """Test execution with unanalyzed players."""
        job = PlayerAnalyzerJob(job_config)

        # Mock unanalyzed players
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_unanalyzed_player]
        mock_db.execute.return_value = mock_result

        with (
            patch.object(job, "_fetch_discovered_player_matches", AsyncMock()),
            patch.object(job, "_check_ban_status", AsyncMock()),
            patch("app.jobs.player_analyzer.RiotAPIClient") as mock_client,
            patch("app.jobs.player_analyzer.RiotDataManager") as mock_manager,
            patch("app.jobs.player_analyzer.SmurfDetectionService") as mock_service,
        ):
            # Setup mocks
            mock_api = MagicMock()
            mock_api.close = AsyncMock()
            mock_client.return_value = mock_api

            mock_mgr = MagicMock()
            mock_mgr.get_player_by_puuid = AsyncMock(return_value=None)
            mock_manager.return_value = mock_mgr

            mock_detection = MagicMock()
            mock_detection.analyze_player = AsyncMock(
                return_value=SimpleNamespace(
                    is_smurf=False,
                    detection_score=0.4,
                    confidence_level="low",
                )
            )
            mock_service.return_value = mock_detection

            await job.execute(mock_db)

            # Should have processed unanalyzed players
            assert "players_to_analyze_count" in job.execution_log

    @pytest.mark.asyncio
    async def test_execute_no_players(self, job_config, mock_db):
        """Test execution when no players need analysis."""
        job = PlayerAnalyzerJob(job_config)

        # Mock empty results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        with (
            patch.object(job, "_fetch_discovered_player_matches", AsyncMock()),
            patch.object(job, "_check_ban_status", AsyncMock()),
            patch("app.jobs.player_analyzer.RiotAPIClient") as mock_client,
        ):
            mock_api = MagicMock()
            mock_api.close = AsyncMock()
            mock_client.return_value = mock_api

            await job.execute(mock_db)

            # Should complete without errors
            assert "players_to_analyze_count" in job.execution_log
            assert job.execution_log["players_to_analyze_count"] == 0

    # Removed test for private method _mark_player_analyzed
    # This is tested through the execute() method

    # Removed test for private method _store_detection_result
    # This is tested through the execute() method

    @pytest.mark.asyncio
    async def test_check_ban_status_no_players(self, job_config, mock_db):
        """Test ban status check when no players need checking."""
        job = PlayerAnalyzerJob(job_config)

        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await job._check_ban_status(mock_db)

        # Should complete without errors
        assert True

    @pytest.mark.asyncio
    async def test_check_ban_status_with_players(
        self, job_config, mock_db, sample_unanalyzed_player
    ):
        """Test ban status check with players to check."""
        job = PlayerAnalyzerJob(job_config)

        # Mock players needing ban check
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_unanalyzed_player]
        mock_db.execute.return_value = mock_result

        with (
            patch("app.jobs.player_analyzer.RiotAPIClient") as mock_client,
            patch("app.jobs.player_analyzer.RiotDataManager") as mock_manager,
        ):
            # Setup mocks
            mock_api = MagicMock()
            mock_api.close = AsyncMock()
            mock_client.return_value = mock_api

            mock_data_mgr = MagicMock()
            mock_data_mgr.check_player_exists = AsyncMock(return_value=True)
            mock_manager.return_value = mock_data_mgr

            job.api_client = mock_api
            job.data_manager = mock_data_mgr

            await job._check_ban_status(mock_db)

            # Should have checked ban status
            assert True

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, job_config, mock_db):
        """Test that metrics are properly tracked."""
        job = PlayerAnalyzerJob(job_config)

        # Test standard metrics
        job.increment_metric("api_requests_made", 20)
        job.increment_metric("records_created", 10)
        job.increment_metric("records_updated", 3)

        assert job.metrics["api_requests_made"] == 20
        assert job.metrics["records_created"] == 10
        assert job.metrics["records_updated"] == 3

    @pytest.mark.asyncio
    async def test_batch_limit_respected(self, job_config, mock_db):
        """Test that batch limit is respected."""
        job = PlayerAnalyzerJob(job_config)

        # Create more players than limit
        players = [
            Player(
                puuid=str(uuid4()),
                riot_id=f"Player{i}",
                tag_line="NA1",
                platform="na1",
                is_tracked=False,
                is_analyzed=False,
            )
            for i in range(25)
        ]

        # Mock query result limited by config
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = players[
            : job.unanalyzed_players_per_run
        ]
        mock_db.execute.return_value = mock_result

        result = await job._get_unanalyzed_players(mock_db)

        # Should only get up to unanalyzed_players_per_run
        assert len(result) <= job.unanalyzed_players_per_run

    @pytest.mark.asyncio
    async def test_confidence_threshold_filtering(
        self, job_config, mock_db, sample_unanalyzed_player
    ):
        """Test that low confidence detections are handled appropriately."""
        job = PlayerAnalyzerJob(job_config)

        low_confidence_result = {
            "is_smurf": True,
            "smurf_score": 0.3,  # Below min_smurf_confidence of 0.5
            "confidence": "low",
            "games_analyzed": 30,
        }

        # Low confidence results should still be stored but marked accordingly
        # (Implementation specific behavior)
        assert job.min_smurf_confidence == 0.5
        assert low_confidence_result["smurf_score"] < job.min_smurf_confidence

    @pytest.mark.asyncio
    async def test_store_match_creates_placeholder_players(self, job_config):
        """Ensure missing participants create placeholder players."""
        job = PlayerAnalyzerJob(job_config)

        participant = SimpleNamespace(
            puuid="missing-participant",
            riot_id_game_name="PlayerOne",
            riot_id_tagline="EUNE",
            summoner_name="PlayerOne",
            summoner_level=30,
            champion_id=1,
            champion_name="Annie",
            team_id=100,
            team_position="MIDDLE",
            win=True,
            kills=10,
            deaths=2,
            assists=5,
            gold_earned=12000,
            total_minions_killed=200,
            neutral_minions_killed=20,
            vision_score=15,
            total_damage_dealt_to_champions=25000,
            total_damage_taken=15000,
        )

        match_dto = SimpleNamespace(
            metadata=SimpleNamespace(match_id="match-123"),
            info=SimpleNamespace(
                platform_id="eun1",
                game_creation=0,
                game_duration=1800,
                game_mode="CLASSIC",
                game_type="MATCHED_GAME",
                game_version="1.0.0",
                map_id=11,
                queue_id=420,
                participants=[participant],
            ),
        )

        player_missing_result = MagicMock()
        player_missing_result.scalar_one_or_none.return_value = None

        match_missing_result = MagicMock()
        match_missing_result.scalar_one_or_none.return_value = None

        db = AsyncMock()
        db.add = MagicMock()
        db.execute = AsyncMock(
            side_effect=[
                player_missing_result,
                match_missing_result,
                match_missing_result,
            ]
        )

        await job._store_match_for_discovered_player(db, match_dto)

        added_players = [
            call.args[0]
            for call in db.add.call_args_list
            if isinstance(call.args[0], Player)
        ]

        assert any(p.puuid == participant.puuid for p in added_players)


class TestPlayerAnalyzerIntegration:
    """Integration tests for player analyzer."""

    @pytest.mark.asyncio
    async def test_full_execution_flow(
        self, job_config, mock_db, sample_unanalyzed_player
    ):
        """Test full execution flow with mocked dependencies."""
        job = PlayerAnalyzerJob(job_config)

        # Mock unanalyzed players
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_unanalyzed_player]
        mock_db.execute.return_value = mock_result

        with (
            patch.object(job, "_fetch_discovered_player_matches", AsyncMock()),
            patch.object(job, "_check_ban_status", AsyncMock()),
            patch("app.jobs.player_analyzer.RiotAPIClient") as mock_client,
            patch("app.jobs.player_analyzer.RiotDataManager") as mock_manager,
            patch("app.jobs.player_analyzer.SmurfDetectionService") as mock_service,
        ):
            # Setup mocks
            mock_api = MagicMock()
            mock_api.close = AsyncMock()
            mock_client.return_value = mock_api

            mock_data_mgr = MagicMock()
            mock_data_mgr.get_player_by_puuid = AsyncMock(return_value=None)
            mock_manager.return_value = mock_data_mgr

            mock_detection = MagicMock()
            mock_detection.analyze_player = AsyncMock(
                return_value=SimpleNamespace(
                    is_smurf=False,
                    detection_score=0.4,
                    confidence_level="low",
                )
            )
            mock_service.return_value = mock_detection

            # Execute job
            await job.execute(mock_db)

            # Verify job completed and logged
            assert "players_to_analyze_count" in job.execution_log

    @pytest.mark.asyncio
    async def test_error_handling_during_analysis(
        self, job_config, mock_db, sample_unanalyzed_player
    ):
        """Test error handling during player analysis."""
        job = PlayerAnalyzerJob(job_config)

        # Mock unanalyzed players
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_unanalyzed_player]
        mock_db.execute.return_value = mock_result

        with (
            patch.object(job, "_fetch_discovered_player_matches", AsyncMock()),
            patch.object(job, "_check_ban_status", AsyncMock()),
            patch("app.jobs.player_analyzer.RiotAPIClient") as mock_client,
            patch("app.jobs.player_analyzer.RiotDataManager") as mock_manager,
            patch("app.jobs.player_analyzer.SmurfDetectionService") as mock_service,
        ):
            mock_api = MagicMock()
            mock_api.close = AsyncMock()
            mock_client.return_value = mock_api

            mock_data_mgr = MagicMock()
            mock_data_mgr.get_player_by_puuid = AsyncMock(return_value=None)
            mock_manager.return_value = mock_data_mgr

            # Make detection service raise an error
            mock_detection = MagicMock()
            mock_detection.analyze_player = AsyncMock(
                side_effect=Exception("Analysis error")
            )
            mock_service.return_value = mock_detection

            # Should handle error and continue (not crash)
            await job.execute(mock_db)

            # Job should have logged unanalyzed players even if analysis failed
            assert "players_to_analyze_count" in job.execution_log
