from app.features.matchmaking_analysis.orm_models import JobExecutionORM
from app.core.enums import JobStatus


def test_job_execution_domain_methods():
    """Test rich domain model methods for JobExecutionORM"""
    job = JobExecutionORM(
        id="test-job-123",
        user_id="user-123",
        job_type="matchmaking_analysis",
        status=JobStatus.PENDING,
    )

    # Test start_analysis method
    job.start_analysis()
    assert job.status == JobStatus.RUNNING
    assert job.started_at is not None

    # Test progress calculation
    progress = job.calculate_progress(100, 25)
    assert progress == 25.0

    # Test edge case - no total matches
    progress_zero = job.calculate_progress(0, 0)
    assert progress_zero == 0.0

    # Test progress cap at 100%
    progress_max = job.calculate_progress(100, 150)
    assert progress_max == 100.0

    # Test failure handling
    job.handle_failure("Test error message")
    assert job.status == JobStatus.FAILED
    assert job.error_message == "Test error message"
    assert job.completed_at is not None
