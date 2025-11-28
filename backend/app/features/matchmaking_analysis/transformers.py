"""Data mapper for matchmaking analysis feature.

Implements three-way transformation:
1. ORM ↔ Pydantic Domain Model (models.py)
2. Domain Model ↔ API Schema (schemas.py)
3. ORM ↔ API Schema (convenience methods)
"""

from typing import List, Dict, Any

from app.features.matchmaking_analysis.orm_models import JobExecutionORM
from app.features.matchmaking_analysis.models import (
    MatchmakingAnalysis,
    MatchmakingMetrics,
    MatchDataPoint,
)
from app.features.matchmaking_analysis.schemas import (
    MatchmakingAnalysisCreate,
    MatchmakingAnalysisResponse,
)
from app.core.enums import JobStatus


class MatchmakingAnalysisTransformer:
    """Data mapper for matchmaking analysis feature.

    Follows Data Mapper pattern to separate domain models from persistence.
    Provides clean boundaries between layers.
    """

    # ========== ORM ↔ Domain Model ==========

    @staticmethod
    def orm_to_domain(orm: JobExecutionORM) -> MatchmakingAnalysis:
        """Transform ORM model to Pydantic domain model.

        :param orm: ORM instance from database
        :returns: Pydantic domain model
        """
        # Handle both enum and string status
        status_value = (
            orm.status.value if hasattr(orm.status, "value") else str(orm.status)
        )

        return MatchmakingAnalysis(
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
    def domain_to_orm(domain: MatchmakingAnalysis, orm: JobExecutionORM) -> None:
        """Update ORM model from Pydantic domain model.

        :param domain: Pydantic domain model with updated data
        :param orm: ORM instance to update (modified in place)
        """
        # Update mutable fields only (ID and timestamps managed by DB)
        orm.status = JobStatus(domain.status) if isinstance(domain.status, str) else domain.status
        orm.parameters = domain.parameters
        orm.result = domain.result
        orm.error_message = domain.error_message
        orm.progress = domain.progress
        orm.matches_analyzed = domain.matches_analyzed
        orm.winrate = domain.winrate
        orm.avg_rank_difference = domain.avg_rank_difference
        orm.fairness_score = domain.fairness_score

        # Update timestamps if changed
        if domain.started_at:
            orm.started_at = domain.started_at
        if domain.completed_at:
            orm.completed_at = domain.completed_at

    # ========== Domain Model ↔ API Schema ==========

    @staticmethod
    def domain_to_response(domain: MatchmakingAnalysis) -> MatchmakingAnalysisResponse:
        """Transform domain model to API response schema.

        :param domain: Pydantic domain model
        :returns: API response schema
        """
        return MatchmakingAnalysisResponse(
            id=domain.id,
            user_id=domain.user_id,
            job_type=domain.job_type,
            status=domain.status,
            parameters=domain.parameters,
            result=domain.result,
            error_message=domain.error_message,
            progress=domain.progress,
            created_at=domain.created_at,
            started_at=domain.started_at,
            completed_at=domain.completed_at,
            matches_analyzed=domain.matches_analyzed,
            winrate=domain.winrate,
            avg_rank_difference=domain.avg_rank_difference,
            fairness_score=domain.fairness_score,
        )

    @staticmethod
    def response_to_domain(response: MatchmakingAnalysisResponse) -> MatchmakingAnalysis:
        """Transform API response schema to domain model.

        :param response: API response schema
        :returns: Pydantic domain model
        """
        return MatchmakingAnalysis(
            id=response.id,
            user_id=response.user_id,
            job_type=response.job_type,
            status=response.status,
            parameters=response.parameters,
            result=response.result,
            error_message=response.error_message,
            progress=response.progress,
            created_at=response.created_at,
            started_at=response.started_at,
            completed_at=response.completed_at,
            matches_analyzed=response.matches_analyzed,
            winrate=response.winrate,
            avg_rank_difference=response.avg_rank_difference,
            fairness_score=response.fairness_score,
        )

    # ========== ORM ↔ API Schema (Convenience) ==========

    @staticmethod
    def orm_to_response(orm: JobExecutionORM) -> MatchmakingAnalysisResponse:
        """Direct transformation from ORM to API response (convenience method).

        :param orm: ORM instance from database
        :returns: API response schema
        """
        domain = MatchmakingAnalysisTransformer.orm_to_domain(orm)
        return MatchmakingAnalysisTransformer.domain_to_response(domain)

    @staticmethod
    def request_to_orm(request: MatchmakingAnalysisCreate) -> JobExecutionORM:
        """Transform API request to ORM model (for creation).

        :param request: API request schema
        :returns: New ORM instance (not persisted)
        """
        return JobExecutionORM(
            user_id=request.user_id,
            job_type="matchmaking_analysis",
            parameters=request.parameters or {},
            status=JobStatus.PENDING,
        )

    # ========== Metrics Transformers ==========

    @staticmethod
    def results_to_metrics(results: Dict[str, Any]) -> MatchmakingMetrics:
        """Transform results dictionary to metrics domain model.

        :param results: Analysis results dictionary
        :returns: Metrics domain model
        """
        return MatchmakingMetrics(
            matches_analyzed=results["matches_analyzed"],
            player_winrate=results["winrate"],
            team_avg_winrate=results["team_avg_winrate"],
            enemy_avg_winrate=results["enemy_avg_winrate"],
            avg_rank_difference=results["avg_rank_difference"],
            fairness_score=results["fairness_score"],
            player_puuid=results["player_puuid"],
            region=results["region"],
        )

    @staticmethod
    def metrics_to_results(metrics: MatchmakingMetrics) -> Dict[str, Any]:
        """Transform metrics domain model to results dictionary.

        :param metrics: Metrics domain model
        :returns: Results dictionary for storage
        """
        return {
            "matches_analyzed": metrics.matches_analyzed,
            "winrate": metrics.player_winrate,
            "team_avg_winrate": metrics.team_avg_winrate,
            "enemy_avg_winrate": metrics.enemy_avg_winrate,
            "avg_rank_difference": metrics.avg_rank_difference,
            "fairness_score": metrics.fairness_score,
            "player_puuid": metrics.player_puuid,
            "region": metrics.region,
        }

    # ========== Batch Transformations ==========

    @staticmethod
    def batch_orm_to_response(orms: List[JobExecutionORM]) -> List[MatchmakingAnalysisResponse]:
        """Batch transform ORM instances to API responses.

        :param orms: List of ORM instances
        :returns: List of API response schemas
        """
        return [
            MatchmakingAnalysisTransformer.orm_to_response(orm)
            for orm in orms
        ]
