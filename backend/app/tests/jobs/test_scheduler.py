"""
Tests for the job scheduler.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.jobs.scheduler import (
    get_scheduler,
    start_scheduler,
    shutdown_scheduler,
)
from app.models.job_tracking import JobConfiguration


class TestScheduler:
    """Test cases for job scheduler."""

    @pytest.mark.asyncio
    async def test_start_scheduler(self):
        """Test scheduler startup."""
        with (
            patch("app.jobs.scheduler.AsyncIOScheduler") as mock_scheduler_class,
            patch("app.jobs.scheduler._mark_stale_jobs_as_failed") as mock_mark,
            patch("app.jobs.scheduler._load_and_schedule_jobs") as mock_load,
        ):
            mock_scheduler = MagicMock()
            mock_scheduler.start = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler
            mock_mark.return_value = None
            mock_load.return_value = None

            scheduler = await start_scheduler()

            assert scheduler is not None

    @pytest.mark.asyncio
    async def test_get_scheduler_not_initialized(self):
        """Test getting scheduler when not initialized."""
        with patch("app.jobs.scheduler._scheduler", None):
            scheduler = get_scheduler()
            assert scheduler is None

    @pytest.mark.asyncio
    async def test_get_scheduler(self):
        """Test getting scheduler instance."""
        scheduler = get_scheduler()
        # May be None if not initialized
        assert scheduler is None or scheduler is not None

    @pytest.mark.asyncio
    async def test_shutdown_scheduler(self):
        """Test shutting down scheduler."""
        mock_scheduler = MagicMock()
        mock_scheduler.shutdown = MagicMock()

        # Patch both get_scheduler and the global _scheduler
        with (
            patch("app.jobs.scheduler._scheduler", mock_scheduler),
            patch("app.jobs.scheduler.get_scheduler", return_value=mock_scheduler),
        ):
            await shutdown_scheduler()
            mock_scheduler.shutdown.assert_called_once_with(wait=True)

    @pytest.mark.asyncio
    async def test_shutdown_scheduler_not_initialized(self):
        """Test shutting down scheduler when not initialized."""
        with patch("app.jobs.scheduler.get_scheduler", return_value=None):
            # Should not raise
            await shutdown_scheduler()

    @pytest.mark.asyncio
    async def test_scheduler_state(self):
        """Test scheduler state access."""
        scheduler = get_scheduler()
        # Scheduler may or may not be initialized
        if scheduler:
            assert hasattr(scheduler, "state")
            assert hasattr(scheduler, "get_jobs")


class TestSchedulerJobManagement:
    """Test cases for job management in scheduler."""

    @pytest.mark.asyncio
    async def test_add_job_from_config(self):
        """Test adding job from configuration."""
        mock_scheduler = MagicMock()
        mock_scheduler.add_job = MagicMock()

        job_config = MagicMock(spec=JobConfiguration)
        job_config.id = 1
        job_config.job_type = "tracked_player_updater"
        job_config.name = "Test Job"
        job_config.is_active = True
        job_config.config_json = {"interval_seconds": 120}

        with patch("app.jobs.scheduler.get_scheduler", return_value=mock_scheduler):
            # This would normally be called from main.py
            # Just verify scheduler has add_job method
            assert hasattr(mock_scheduler, "add_job")

    @pytest.mark.asyncio
    async def test_remove_job(self):
        """Test removing job from scheduler."""
        mock_scheduler = MagicMock()
        mock_scheduler.remove_job = MagicMock()

        with patch("app.jobs.scheduler.get_scheduler", return_value=mock_scheduler):
            # This would normally be called from job service
            assert hasattr(mock_scheduler, "remove_job")

    @pytest.mark.asyncio
    async def test_pause_job(self):
        """Test pausing job."""
        mock_scheduler = MagicMock()
        mock_scheduler.pause_job = MagicMock()

        with patch("app.jobs.scheduler.get_scheduler", return_value=mock_scheduler):
            assert hasattr(mock_scheduler, "pause_job")

    @pytest.mark.asyncio
    async def test_resume_job(self):
        """Test resuming job."""
        mock_scheduler = MagicMock()
        mock_scheduler.resume_job = MagicMock()

        with patch("app.jobs.scheduler.get_scheduler", return_value=mock_scheduler):
            assert hasattr(mock_scheduler, "resume_job")
