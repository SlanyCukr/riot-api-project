"""Analysis orchestrator for coordinating matchmaking analysis workflow."""

from typing import Dict, Any, List
import structlog

from app.features.matchmaking_analysis.repository import MatchmakingAnalysisRepositoryInterface
from app.features.matchmaking_analysis.gateway import MatchmakingGateway
from app.features.matchmaking_analysis.match_data_processor import MatchDataProcessor
from app.features.matchmaking_analysis.fairness_calculator import FairnessCalculator
from app.features.matchmaking_analysis.schemas import AnalysisParameters, MatchDataValidation
from app.core.enums import JobStatus

logger = structlog.get_logger(__name__)


class AnalysisOrchestrator:
    """Orchestrates the matchmaking analysis workflow."""

    def __init__(
        self,
        repository: MatchmakingAnalysisRepositoryInterface,
        gateway: MatchmakingGateway,
        match_processor: MatchDataProcessor,
        fairness_calculator: FairnessCalculator,
        parameter_schema: type[AnalysisParameters] = AnalysisParameters,
    ):
        self.repository = repository
        self.gateway = gateway
        self.match_processor = match_processor
        self.fairness_calculator = fairness_calculator
        self.parameter_schema = parameter_schema

    async def execute_analysis(self, analysis_id: str) -> None:
        """Execute complete matchmaking analysis workflow with error handling.

        :param analysis_id: ID of the analysis job to execute
        :raises MatchmakingAnalysisError: If analysis execution fails
        """
        from app.core.exceptions import MatchmakingAnalysisError

        # Get the analysis job
        job = await self.repository.get_analysis_by_id(analysis_id)
        if not job:
            logger.warning("analysis_job_not_found", analysis_id=analysis_id)
            raise MatchmakingAnalysisError(
                message=f"Analysis job {analysis_id} not found",
                operation="execute_analysis",
                context={"analysis_id": analysis_id},
            )

        try:
            # Start the analysis
            await self._start_analysis(job, analysis_id)

            # Validate and extract parameters using Pydantic
            params_dict = job.parameters or {}
            try:
                params = self.parameter_schema.model_validate(params_dict)
            except Exception as e:
                raise MatchmakingAnalysisError(
                    message=f"Invalid analysis parameters: {str(e)}",
                    operation="validate_parameters",
                    context={"parameters": params_dict},
                    original_error=e,
                )

            # Fetch and validate matches
            matches = await self._fetch_matches(
                params.puuid,
                getattr(params, 'match_count', 20)
            )
            validated_matches = MatchDataValidation.filter_valid_matches(matches)

            if not validated_matches:
                raise MatchmakingAnalysisError(
                    message="No valid matches found for analysis",
                    operation="fetch_matches",
                    context={
                        "puuid": params.puuid,
                        "total_matches": len(matches),
                        "valid_matches": 0,
                    },
                )

            logger.info(
                "matches_validated",
                analysis_id=analysis_id,
                total_matches=len(matches),
                valid_matches=len(validated_matches),
            )

            # Process matches and calculate metrics
            analysis_results = await self._process_matches(
                validated_matches, params.model_dump(), job, analysis_id
            )

            # Save results and complete
            await self.repository.save_analysis_results(analysis_id, analysis_results)
            await self.repository.update_analysis_status(analysis_id, JobStatus.SUCCESS)

            logger.info(
                "analysis_completed",
                analysis_id=analysis_id,
                matches_analyzed=analysis_results.get("matches_analyzed", 0),
                fairness_score=analysis_results.get("fairness_score"),
            )

        except MatchmakingAnalysisError as e:
            # Re-raise our custom errors
            await self._handle_analysis_failure(job, analysis_id, str(e))
            raise
        except Exception as e:
            # Wrap unexpected errors
            logger.error(
                "unexpected_analysis_error",
                analysis_id=analysis_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            await self._handle_analysis_failure(job, analysis_id, str(e))
            raise MatchmakingAnalysisError(
                message=f"Unexpected error during analysis: {str(e)}",
                operation="execute_analysis",
                context={"analysis_id": analysis_id},
                original_error=e,
            )

    async def _start_analysis(self, job: Any, analysis_id: str) -> None:
        """Start the analysis and update status.

        Args:
            job: Analysis job object
            analysis_id: Analysis ID
        """
        job.start_analysis()
        await self.repository.update_analysis_status(analysis_id, JobStatus.RUNNING)

    async def _fetch_matches(self, player_puuid: str, match_count: int = 50) -> List[Dict[str, Any]]:
        """Fetch player's recent matches.

        Args:
            player_puuid: Player's PUUID
            match_count: Number of matches to fetch

        Returns:
            List of match data
        """
        return await self.gateway.get_player_recent_matches(player_puuid, match_count)

    async def _process_matches(
        self, matches: List[Dict[str, Any]], params: Dict[str, Any], job: Any, analysis_id: str
    ) -> Dict[str, Any]:
        """Process all matches and calculate analysis metrics with progress persistence.

        Args:
            matches: List of matches to process
            params: Validated analysis parameters
            job: Analysis job object
            analysis_id: Analysis ID

        Returns:
            Dict with analysis results
        """
        total_matches = len(matches)
        processed_matches = 0

        # Initialize results collection
        team_winrates: List[float] = []
        enemy_winrates: List[float] = []
        rank_differences: List[float] = []
        player_wins: List[bool] = []

        # Process each match
        for i, match in enumerate(matches):
            try:
                match_result = await self._process_single_match(match, params["puuid"])

                if match_result:
                    team_winrates.extend(match_result["team_winrates"])
                    enemy_winrates.extend(match_result["enemy_winrates"])
                    rank_differences.append(match_result["rank_difference"])
                    player_wins.append(match_result["player_win"])

                processed_matches += 1

                # Update progress every 5 matches or on last match
                if processed_matches % 5 == 0 or processed_matches == total_matches:
                    progress = job.calculate_progress(total_matches, processed_matches)
                    job.progress = progress

                    # Persist progress to database
                    updated_job = await self.repository.update_analysis_progress(
                        analysis_id, progress
                    )

                    if updated_job:
                        logger.info(
                            "progress_persisted",
                            analysis_id=analysis_id,
                            progress=progress,
                            processed=processed_matches,
                            total=total_matches,
                        )

            except Exception as e:
                logger.error(
                    "match_processing_error",
                    match_id=match.get("matchId"),
                    error=str(e),
                    error_type=type(e).__name__,
                )
                continue

        # Calculate final metrics
        return self._calculate_final_metrics(
            team_winrates, enemy_winrates, rank_differences, player_wins, params
        )

    async def _process_single_match(self, match: Dict[str, Any], player_puuid: str) -> Dict[str, Any] | None:
        """Process a single match and extract metrics.

        Args:
            match: Match data
            player_puuid: Target player's PUUID

        Returns:
            Match metrics dict or None if processing failed
        """
        match_data = await self.gateway.fetch_match_data(match["matchId"])

        if not match_data or not MatchDataValidation.validate_match_structure(match_data):
            return None

        # Pass the database session from repository to match processor
        return await self.match_processor.process_match_data(
            match_data, player_puuid, self.repository.db
        )

    def _calculate_final_metrics(
        self,
        team_winrates: List[float],
        enemy_winrates: List[float],
        rank_differences: List[float],
        player_wins: List[bool],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Calculate final analysis metrics from processed match data.

        Args:
            team_winrates: List of team winrates
            enemy_winrates: List of enemy winrates
            rank_differences: List of rank differences
            player_wins: List of player win results
            params: Analysis parameters

        Returns:
            Dict with final analysis results
        """
        # Calculate metrics using fairness calculator
        player_winrate = self.fairness_calculator.calculate_player_winrate(player_wins)
        team_avg_winrate = self.fairness_calculator.calculate_average_winrate(team_winrates)
        enemy_avg_winrate = self.fairness_calculator.calculate_average_winrate(enemy_winrates)
        avg_rank_difference = self.fairness_calculator.calculate_average_rank_difference(rank_differences)
        fairness_score = self.fairness_calculator.calculate_fairness_score(
            team_avg_winrate, enemy_avg_winrate, avg_rank_difference
        )

        return {
            "matches_analyzed": len(player_wins),
            "player_puuid": params["puuid"],
            "region": params["region"],
            "winrate": player_winrate,
            "team_avg_winrate": team_avg_winrate,
            "enemy_avg_winrate": enemy_avg_winrate,
            "avg_rank_difference": avg_rank_difference,
            "fairness_score": fairness_score,
        }

    async def _handle_analysis_failure(self, job: Any, analysis_id: str, error_msg: str) -> None:
        """Handle analysis failure.

        Args:
            job: Analysis job object
            analysis_id: Analysis ID
            error_msg: Error message
        """
        formatted_error = f"Analysis failed: {error_msg}"
        job.handle_failure(formatted_error)
        await self.repository.update_analysis_status(analysis_id, JobStatus.FAILED)

        logger.error(
            "analysis_failed",
            analysis_id=analysis_id,
            error=error_msg,
        )