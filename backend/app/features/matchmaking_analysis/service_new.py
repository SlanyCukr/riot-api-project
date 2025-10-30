from typing import List, Optional
import structlog

from app.features.matchmaking_analysis.repository import (
    MatchmakingAnalysisRepositoryInterface,
)
from app.features.matchmaking_analysis.gateway import MatchmakingGateway
from app.features.matchmaking_analysis.transformers import (
    MatchmakingAnalysisTransformer,
)
from app.features.matchmaking_analysis.schemas import (
    MatchmakingAnalysisCreate,
    MatchmakingAnalysisResponse,
)
from app.core.enums import JobStatus

logger = structlog.get_logger()


class MatchmakingAnalysisService:
    """Enterprise service for matchmaking analysis with clean separation of concerns"""

    def __init__(
        self,
        repository: MatchmakingAnalysisRepositoryInterface,
        gateway: MatchmakingGateway,
        transformer: MatchmakingAnalysisTransformer,
    ):
        self.repository = repository
        self.gateway = gateway
        self.transformer = transformer

    async def start_analysis(
        self, request: MatchmakingAnalysisCreate
    ) -> MatchmakingAnalysisResponse:
        """Start a new matchmaking analysis - pure orchestration"""
        # Create analysis job through repository
        job_orm = await self.repository.create_analysis(request)

        # Transform to response
        response = self.transformer.orm_to_response(job_orm)

        # Queue background job (implementation will be in next task)
        # For now, just return the created job
        return response

    async def get_analysis_status(
        self, analysis_id: str
    ) -> Optional[MatchmakingAnalysisResponse]:
        """Get current analysis status"""
        job_orm = await self.repository.get_analysis_by_id(analysis_id)
        if not job_orm:
            return None

        return self.transformer.orm_to_response(job_orm)

    async def get_user_analyses(
        self, user_id: str, limit: int = 50
    ) -> List[MatchmakingAnalysisResponse]:
        """Get user's analysis history"""
        jobs = await self.repository.get_user_analyses(user_id, limit)
        return [self.transformer.orm_to_response(job) for job in jobs]

    async def execute_background_analysis(self, analysis_id: str) -> None:
        """Execute the actual matchmaking analysis in background"""
        # Get the analysis job
        job = await self.repository.get_analysis_by_id(analysis_id)
        if not job:
            return

        try:
            # Start the analysis
            job.start_analysis()
            await self.repository.update_analysis_status(analysis_id, JobStatus.RUNNING)

            # Get analysis parameters
            params = job.parameters or {}
            region = params.get("region", "na")
            player_puuid = params.get("puuid")

            if not player_puuid:
                raise ValueError("PUUID is required for analysis")

            # Fetch player's recent matches
            matches = await self.gateway.get_player_recent_matches(player_puuid, 50)

            if not matches:
                raise ValueError("No matches found for analysis")

            # Analyze matches (simplified version - full logic will be implemented later)
            total_matches = len(matches)
            processed_matches = 0

            analysis_results = {
                "matches_analyzed": total_matches,
                "player_puuid": player_puuid,
                "region": region,
            }

            # Process each match (simplified - real implementation would be more complex)
            for match in matches:
                try:
                    match_data = await self.gateway.fetch_match_data(match["matchId"])
                    if match_data:
                        # Process match data
                        processed_matches += 1

                        # Update progress
                        progress = job.calculate_progress(
                            total_matches, processed_matches
                        )
                        job.progress = progress

                        # For now, just count matches - real analysis would calculate metrics
                        # TODO: Implement actual matchmaking fairness calculations

                except Exception as e:
                    logger.error(
                        "match_processing_error",
                        match_id=match.get("matchId"),
                        error=str(e),
                    )
                    continue

            # Calculate final results (placeholder for now)
            # TODO: Implement actual matchmaking analysis calculations
            # TODO: Calculate real winrate from match data
            # TODO: Calculate actual rank difference between teams
            # TODO: Implement fairness score algorithm based on rank distribution
            analysis_results.update(
                {
                    "winrate": 0.5,  # Placeholder - will be calculated from actual match results
                    "avg_rank_difference": 25.0,  # Placeholder - will be calculated from team rank differences
                    "fairness_score": 0.7,  # Placeholder - will be calculated using fairness algorithm
                }
            )

            # Save results
            await self.repository.save_analysis_results(analysis_id, analysis_results)
            await self.repository.update_analysis_status(analysis_id, JobStatus.SUCCESS)

        except Exception as e:
            # Handle failure
            error_msg = f"Analysis failed: {str(e)}"
            job.handle_failure(error_msg)
            await self.repository.update_analysis_status(analysis_id, JobStatus.FAILED)
