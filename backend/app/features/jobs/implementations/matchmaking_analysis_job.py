"""Background job for executing matchmaking analysis."""

from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.features.jobs.base import BaseJob
from app.features.jobs.error_handling import handle_riot_api_errors
from app.features.matchmaking_analysis.dependencies import (
    get_matchmaking_analysis_repository,
)
from app.features.matchmaking_analysis.gateway import MatchmakingGateway
from app.features.matchmaking_analysis.service import MatchmakingAnalysisService
from app.features.matchmaking_analysis.transformers import MatchmakingAnalysisTransformer
from app.core.riot_api.client import RiotAPIClient
from app.core.riot_api.data_manager import RiotDataManager
from app.core import get_riot_api_key


logger = structlog.get_logger(__name__)


class MatchmakingAnalysisJob(BaseJob):
    """Background job for executing matchmaking analysis workflow.

    Runs the complete analysis process in background, updating progress
    and handling errors appropriately.
    """

    def __init__(self, job_config_id: int, analysis_id: str):
        """Initialize job with analysis ID.

        :param job_config_id: Job configuration ID
        :param analysis_id: Matchmaking analysis job ID to execute
        """
        super().__init__(job_config_id)
        self.analysis_id = analysis_id

    @handle_riot_api_errors(
        operation="matchmaking_analysis",
        critical=True,
        log_context=lambda self: {"analysis_id": self.analysis_id},
    )
    async def execute(self, db: AsyncSession) -> None:
        """Execute the matchmaking analysis job.

        :param db: Database session for job execution
        """
        logger.info(
            "matchmaking_analysis_job_started",
            analysis_id=self.analysis_id,
            job_config_id=self.job_config_id,
        )

        try:
            # Initialize all dependencies manually (no DI in background context)
            repository = get_matchmaking_analysis_repository(db)

            # Create Riot API client and data manager directly (like other jobs)
            api_key = await get_riot_api_key(db)
            riot_client = RiotAPIClient(api_key=api_key)
            data_manager = RiotDataManager(db, riot_client)
            gateway = MatchmakingGateway(riot_client, data_manager)
            transformer = MatchmakingAnalysisTransformer()

            # Get service with all dependencies
            service = MatchmakingAnalysisService(
                repository=repository,
                gateway=gateway,
                transformer=transformer,
                db=db,
            )

            # Execute analysis workflow
            await service.execute_background_analysis(self.analysis_id)

            # Track metrics
            self.increment_metric("records_updated", 1)

            logger.info(
                "matchmaking_analysis_job_completed",
                analysis_id=self.analysis_id,
            )

        except Exception as e:
            logger.error(
                "matchmaking_analysis_job_failed",
                analysis_id=self.analysis_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
