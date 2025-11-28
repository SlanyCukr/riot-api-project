from datetime import datetime, timezone
from app.features.matchmaking_analysis.transformers import (
    MatchmakingAnalysisTransformer,
)
from app.features.matchmaking_analysis.orm_models import JobExecutionORM
from app.features.matchmaking_analysis.schemas import (
    MatchmakingAnalysisCreate,
    MatchmakingAnalysisResponse,
)
from app.core.enums import JobStatus


def test_transform_orm_to_response():
    """Test transforming ORM model to API response"""
    # Setup
    orm_job = JobExecutionORM(
        id="job-123",
        user_id="user-123",
        job_type="matchmaking_analysis",
        status=JobStatus.SUCCESS,
        progress=100.0,
        winrate=0.65,
        avg_rank_difference=12.5,
        fairness_score=0.78,
        matches_analyzed=50,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )

    # Execute
    response = MatchmakingAnalysisTransformer.orm_to_response(orm_job)

    # Verify
    assert isinstance(response, MatchmakingAnalysisResponse)
    assert response.id == "job-123"
    assert response.user_id == "user-123"
    assert response.winrate == 0.65
    assert response.avg_rank_difference == 12.5
    assert response.fairness_score == 0.78
    assert response.matches_analyzed == 50


def test_transform_request_to_orm():
    """Test transforming API request to ORM model"""
    # Setup
    request = MatchmakingAnalysisCreate(
        user_id="user-123", parameters={"region": "na", "queue": "ranked"}
    )

    # Execute
    orm_job = MatchmakingAnalysisTransformer.request_to_orm(request)

    # Verify
    assert isinstance(orm_job, JobExecutionORM)
    assert orm_job.user_id == "user-123"
    assert orm_job.job_type == "matchmaking_analysis"
    assert orm_job.parameters == {"region": "na", "queue": "ranked"}
    assert orm_job.status == JobStatus.PENDING  # Default status


def test_batch_transform_participants():
    """Test bulk transformation of participant data"""
    # Setup
    participants = [
        {
            "puuid": "puuid-1",
            "summonerId": "summoner-1",
            "rank": "GOLD",
            "tier": "II",
            "wins": 25,
            "losses": 15,
        },
        {
            "puuid": "puuid-2",
            "summonerId": "summoner-2",
            "rank": "SILVER",
            "tier": "I",
            "wins": 10,
            "losses": 20,
        },
    ]

    # Execute
    transformed = MatchmakingAnalysisTransformer.batch_transform_participants(
        participants
    )

    # Verify
    assert len(transformed) == 2
    assert transformed[0]["puuid"] == "puuid-1"
    assert transformed[0]["summoner_id"] == "summoner-1"
    assert transformed[0]["rank"] == "GOLD"
    assert transformed[0]["wins"] == 25
    assert transformed[1]["puuid"] == "puuid-2"
    assert transformed[1]["losses"] == 20
