from typing import List, Dict, Any, cast

from app.features.matchmaking_analysis.orm_models import JobExecutionORM
from app.features.matchmaking_analysis.schemas import (
    MatchmakingAnalysisCreate,
    MatchmakingAnalysisResponse,
)


class MatchmakingAnalysisTransformer:
    """Data mapper for matchmaking analysis feature"""

    @staticmethod
    def orm_to_response(orm: JobExecutionORM) -> MatchmakingAnalysisResponse:
        """Transform ORM model to API response"""
        # Handle both enum and string status
        status_value = (
            orm.status.value if hasattr(orm.status, "value") else str(orm.status)
        )

        return MatchmakingAnalysisResponse(
            id=orm.id,
            user_id=orm.user_id,
            job_type=orm.job_type,
            status=status_value,
            parameters=orm.parameters,
            result=orm.result,
            error_message=orm.error_message,
            progress=orm.progress or 0.0,
            created_at=orm.created_at,
            started_at=orm.started_at,
            completed_at=orm.completed_at,
            matches_analyzed=orm.matches_analyzed,
            winrate=orm.winrate,
            avg_rank_difference=orm.avg_rank_difference,
            fairness_score=orm.fairness_score,
        )

    @staticmethod
    def request_to_orm(request: MatchmakingAnalysisCreate) -> JobExecutionORM:
        """Transform API request to ORM model"""
        from app.core.enums import JobStatus

        return JobExecutionORM(
            user_id=request.user_id,
            job_type="matchmaking_analysis",
            parameters=request.parameters or {},
            status=JobStatus.PENDING,
        )

    @staticmethod
    def batch_transform_participants(participants: List[Any]) -> List[Dict[str, Any]]:
        """Handle bulk transformations for participant data"""
        transformed: List[Dict[str, Any]] = []
        for participant in participants:
            # Transform participant data based on actual structure
            participant_dict = cast(Dict[str, Any], participant)
            transformed.append(
                {
                    "puuid": participant_dict.get("puuid"),
                    "summoner_id": participant_dict.get("summonerId"),
                    "rank": participant_dict.get("rank"),
                    "tier": participant_dict.get("tier"),
                    "wins": participant_dict.get("wins", 0),
                    "losses": participant_dict.get("losses", 0),
                }
            )
        return transformed
