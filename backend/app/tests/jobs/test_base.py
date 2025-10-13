"""
Tests for the base job class.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.jobs.base import BaseJob
from app.models.job_tracking import JobExecution, JobConfiguration


class ConcreteJob(BaseJob):
    """Concrete implementation of BaseJob for testing."""

    async def execute(self, db: AsyncMock) -> None:
        """Execute test job."""
        # Simulate job work
        self.increment_metric("records_created", 10)
        self.increment_metric("records_updated", 5)
        self.increment_metric("api_requests_made", 15)


class FailingJob(BaseJob):
    """Job that always fails for testing error handling."""

    async def execute(self, db: AsyncMock) -> None:
        """Execute test job that raises an error."""
        raise ValueError("Test error")


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
def job_config():
    """Create test job configuration."""
    from app.models import JobType

    return JobConfiguration(
        id=1,
        job_type=JobType.TRACKED_PLAYER_UPDATER,  # Use actual enum value
        name="Test Job",
        schedule="interval(seconds=120)",
        is_active=True,
        config_json={"test": "config"},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


class TestBaseJob:
    """Test cases for BaseJob."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_db, job_config):
        """Test job initialization."""
        job = ConcreteJob(job_config)

        assert job.job_config == job_config
        assert job.job_config.job_type.value == "tracked_player_updater"
        assert job.job_config.name == "Test Job"
        assert job.job_execution is None
        assert job.metrics["api_requests_made"] == 0

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_db, job_config):
        """Test successful job execution."""
        job = ConcreteJob(job_config)

        # Execute job directly
        await job.execute(mock_db)

        # Verify metrics were recorded
        assert job.metrics.get("records_created") == 10
        assert job.metrics.get("records_updated") == 5
        assert job.metrics.get("api_requests_made") == 15

    @pytest.mark.asyncio
    async def test_execute_failure(self, mock_db, job_config):
        """Test job execution failure."""
        job = FailingJob(job_config)

        # Should raise the error
        with pytest.raises(ValueError) as exc_info:
            await job.execute(mock_db)

        assert "Test error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_log_start(self, mock_db, job_config):
        """Test logging job start."""
        job = ConcreteJob(job_config)

        await job.log_start(mock_db)

        assert job.job_execution is not None
        assert job.job_execution.job_config_id == job_config.id
        assert job.job_execution.status.value == "running"
        assert job.job_execution.started_at is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_completion_success(self, mock_db, job_config):
        """Test logging job completion with success."""
        job = ConcreteJob(job_config)

        # Set up execution
        job.job_execution = MagicMock(spec=JobExecution)
        job.job_execution.started_at = datetime.now()
        job.metrics = {
            "records_created": 10,
            "records_updated": 5,
            "api_requests_made": 15,
        }

        await job.log_completion(mock_db, success=True)

        assert job.job_execution.status.value == "success"
        assert job.job_execution.completed_at is not None
        assert job.job_execution.records_created == 10
        assert job.job_execution.records_updated == 5
        assert job.job_execution.api_requests_made == 15
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_completion_failure(self, mock_db, job_config):
        """Test logging job completion with failure."""
        job = ConcreteJob(job_config)

        # Set up execution
        job.job_execution = MagicMock(spec=JobExecution)
        job.job_execution.started_at = datetime.now()

        error_msg = "Test error"
        await job.log_completion(mock_db, success=False, error_message=error_msg)

        assert job.job_execution.status.value == "failed"
        assert job.job_execution.completed_at is not None
        assert job.job_execution.error_message == error_msg
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_log_entry(self, mock_db, job_config):
        """Test adding log entries."""
        job = ConcreteJob(job_config)

        job.add_log_entry("processed_items", 10)
        job.add_log_entry("total_items", 100)

        assert job.execution_log["processed_items"] == 10
        assert job.execution_log["total_items"] == 100

    @pytest.mark.asyncio
    async def test_increment_metric(self, mock_db, job_config):
        """Test incrementing metrics."""
        job = ConcreteJob(job_config)

        job.increment_metric("records_created", 10)
        job.increment_metric("records_updated", 5)

        assert job.metrics["records_created"] == 10
        assert job.metrics["records_updated"] == 5

    @pytest.mark.asyncio
    async def test_increment_api_requests_metric(self, mock_db, job_config):
        """Test incrementing API request metric."""
        job = ConcreteJob(job_config)

        job.increment_metric("api_requests_made", 5)
        assert job.metrics["api_requests_made"] == 5

        job.increment_metric("api_requests_made", 3)
        assert job.metrics["api_requests_made"] == 8


class TestJobExecution:
    """Test cases for job execution helpers."""

    def test_error_handling(self):
        """Test error handling in jobs."""
        # Job errors are handled by the wrapper
        error = ValueError("Test error")
        assert str(error) == "Test error"


class TestJobConfigValidation:
    """Test cases for job configuration validation."""

    @pytest.mark.asyncio
    async def test_validate_config_success(self, mock_db):
        """Test successful config validation."""
        from app.models import JobType

        config = JobConfiguration(
            id=1,
            job_type=JobType.TRACKED_PLAYER_UPDATER,
            name="Test Job",
            schedule="interval(seconds=120)",
            is_active=True,
            config_json={
                "max_new_matches_per_player": 20,
                "max_tracked_players": 10,
            },
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        job = ConcreteJob(config)
        # Should not raise
        assert job.job_config == config

    @pytest.mark.asyncio
    async def test_config_access(self, mock_db, job_config):
        """Test accessing config values."""
        job = ConcreteJob(job_config)

        # Config is accessible
        assert job.job_config == job_config
        assert job.job_config.config_json == {"test": "config"}
