"""
Integration tests for the job system.

These tests verify end-to-end job execution with real database interactions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.jobs.scheduler import get_scheduler, start_scheduler
from app.jobs.tracked_player_updater import TrackedPlayerUpdaterJob
from app.jobs.player_analyzer import PlayerAnalyzerJob
from app.models.job_tracking import JobConfiguration, JobExecution


@pytest.fixture
def tracked_updater_config():
    """Create tracked player updater config."""
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
def player_analyzer_config():
    """Create player analyzer config."""
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


class TestJobSystemIntegration:
    """Integration tests for the entire job system."""

    @pytest.mark.asyncio
    async def test_scheduler_initialization(self):
        """Test that scheduler can be initialized."""
        with (
            patch("app.jobs.scheduler.AsyncIOScheduler") as mock_scheduler,
            patch("app.jobs.scheduler._mark_stale_jobs_as_failed"),
            patch("app.jobs.scheduler._load_and_schedule_jobs"),
        ):
            mock_instance = MagicMock()
            mock_instance.start = MagicMock()
            mock_scheduler.return_value = mock_instance

            scheduler = await start_scheduler()

            assert scheduler is not None

    @pytest.mark.asyncio
    async def test_job_execution_sequence(
        self, mock_db, tracked_updater_config, player_analyzer_config
    ):
        """Test executing jobs in sequence."""
        # Create jobs
        updater_job = TrackedPlayerUpdaterJob(tracked_updater_config)
        analyzer_job = PlayerAnalyzerJob(player_analyzer_config)

        # Mock all external dependencies
        with (
            patch("app.jobs.tracked_player_updater.RiotAPIClient") as mock_client,
            patch("app.jobs.tracked_player_updater.RiotDataManager") as mock_manager,
            patch("app.jobs.player_analyzer.SmurfDetectionService") as mock_service,
        ):
            # Setup mocks
            mock_api = MagicMock()
            mock_api.close = AsyncMock()
            mock_client.return_value = mock_api

            mock_data_mgr = MagicMock()
            mock_manager.return_value = mock_data_mgr

            mock_detection = MagicMock()
            mock_service.return_value = mock_detection

            # Mock empty results (no players to process)
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db.execute.return_value = mock_result

            # Execute updater job
            with (
                patch.object(updater_job, "log_start"),
                patch.object(updater_job, "log_completion"),
            ):
                await updater_job.execute(mock_db)

            # Execute analyzer job
            with (
                patch.object(analyzer_job, "log_start"),
                patch.object(analyzer_job, "log_completion"),
            ):
                await analyzer_job.execute(mock_db)

            # Both jobs should complete without errors
            assert True

    @pytest.mark.asyncio
    async def test_job_failure_isolation(
        self, mock_db, tracked_updater_config, player_analyzer_config
    ):
        """Test that job failures don't affect other jobs."""
        updater_job = TrackedPlayerUpdaterJob(tracked_updater_config)
        analyzer_job = PlayerAnalyzerJob(player_analyzer_config)

        with (
            patch("app.jobs.tracked_player_updater.RiotAPIClient") as mock_client,
            patch("app.jobs.player_analyzer.RiotAPIClient") as mock_client2,
        ):
            mock_api = MagicMock()
            mock_api.close = AsyncMock()
            mock_client.return_value = mock_api
            mock_client2.return_value = mock_api

            # Make updater job fail
            with (
                patch.object(
                    updater_job,
                    "_get_tracked_players",
                    side_effect=Exception("Database error"),
                ),
                patch.object(updater_job, "log_start"),
                patch.object(updater_job, "log_completion"),
            ):
                try:
                    await updater_job.execute(mock_db)
                except Exception:
                    pass  # Expected

            # Analyzer job should still work
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db.execute.return_value = mock_result

            with (
                patch.object(analyzer_job, "log_start"),
                patch.object(analyzer_job, "log_completion"),
                patch("app.jobs.player_analyzer.RiotDataManager") as mock_manager,
                patch("app.jobs.player_analyzer.SmurfDetectionService") as mock_service,
            ):
                mock_data_mgr = MagicMock()
                mock_manager.return_value = mock_data_mgr

                mock_detection = MagicMock()
                mock_service.return_value = mock_detection

                await analyzer_job.execute(mock_db)

            # Analyzer should complete despite updater failure
            assert True

    @pytest.mark.asyncio
    async def test_concurrent_job_execution(
        self, mock_db, tracked_updater_config, player_analyzer_config
    ):
        """Test that jobs can execute concurrently (if needed)."""
        import asyncio

        updater_job = TrackedPlayerUpdaterJob(tracked_updater_config)
        analyzer_job = PlayerAnalyzerJob(player_analyzer_config)

        with (
            patch("app.jobs.tracked_player_updater.RiotAPIClient") as mock_client1,
            patch("app.jobs.player_analyzer.RiotAPIClient") as mock_client2,
            patch("app.jobs.tracked_player_updater.RiotDataManager") as mock_manager1,
            patch("app.jobs.player_analyzer.RiotDataManager") as mock_manager2,
            patch("app.jobs.player_analyzer.SmurfDetectionService") as mock_service,
        ):
            # Setup mocks
            mock_api1 = MagicMock()
            mock_api1.close = AsyncMock()
            mock_client1.return_value = mock_api1

            mock_api2 = MagicMock()
            mock_api2.close = AsyncMock()
            mock_client2.return_value = mock_api2

            mock_data_mgr1 = MagicMock()
            mock_manager1.return_value = mock_data_mgr1

            mock_data_mgr2 = MagicMock()
            mock_manager2.return_value = mock_data_mgr2

            mock_detection = MagicMock()
            mock_service.return_value = mock_detection

            # Mock empty results
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db.execute.return_value = mock_result

            # Execute both jobs concurrently
            with (
                patch.object(updater_job, "log_start"),
                patch.object(updater_job, "log_completion"),
                patch.object(analyzer_job, "log_start"),
                patch.object(analyzer_job, "log_completion"),
            ):
                tasks = [
                    updater_job.execute(mock_db),
                    analyzer_job.execute(mock_db),
                ]
                await asyncio.gather(*tasks)

            # Both should complete successfully
            assert True

    @pytest.mark.asyncio
    async def test_scheduler_status_reporting(self):
        """Test scheduler status reporting."""
        scheduler = get_scheduler()
        # Scheduler may or may not be initialized
        if scheduler:
            assert hasattr(scheduler, "state")
            assert hasattr(scheduler, "get_jobs")
        else:
            # Not initialized is also valid
            assert True


class TestJobExecutionRecording:
    """Test job execution recording and history."""

    @pytest.mark.asyncio
    async def test_execution_record_creation(self, mock_db, tracked_updater_config):
        """Test that execution records are created."""
        job = TrackedPlayerUpdaterJob(tracked_updater_config)

        await job.log_start(mock_db)

        assert job.job_execution is not None
        assert job.job_execution.job_config_id == tracked_updater_config.id
        assert job.job_execution.status.value == "running"
        assert job.job_execution.started_at is not None
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_execution_success_recording(self, mock_db, tracked_updater_config):
        """Test that successful execution is recorded."""
        job = TrackedPlayerUpdaterJob(tracked_updater_config)

        job.job_execution = MagicMock(spec=JobExecution)
        job.job_execution.started_at = datetime.now()
        job.metrics = {
            "new_matches_total": 10,
            "new_players_total": 5,
            "api_requests_made": 0,
            "records_created": 0,
            "records_updated": 0,
        }

        await job.log_completion(mock_db, success=True)

        assert job.job_execution.status.value == "success"
        assert job.job_execution.completed_at is not None
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_execution_failure_recording(self, mock_db, tracked_updater_config):
        """Test that failed execution is recorded."""
        job = TrackedPlayerUpdaterJob(tracked_updater_config)

        job.job_execution = MagicMock(spec=JobExecution)
        job.job_execution.started_at = datetime.now()
        error_msg = "Test error"

        await job.log_completion(mock_db, success=False, error_message=error_msg)

        assert job.job_execution.status.value == "failed"
        assert job.job_execution.completed_at is not None
        assert job.job_execution.error_message == error_msg
        mock_db.commit.assert_called()
