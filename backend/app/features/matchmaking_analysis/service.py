"""Service layer for matchmaking analysis with transaction management."""

from typing import List, Optional
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

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
from app.features.matchmaking_analysis.analysis_orchestrator import AnalysisOrchestrator
from app.features.matchmaking_analysis.match_data_processor import MatchDataProcessor
from app.features.matchmaking_analysis.fairness_calculator import FairnessCalculator
from app.features.matchmaking_analysis.schemas import AnalysisParameters
from app.core.decorators import service_error_handler
from app.core.exceptions import ServiceException

logger = structlog.get_logger(__name__)


class MatchmakingAnalysisService:
    """Enterprise service for matchmaking analysis with transaction management.

    Responsibilities:
    - Orchestrate operations across repository and external services
    - Manage transaction boundaries (commit/rollback)
    - Transform between domain models and API schemas
    - Handle errors and logging
    """

    def __init__(
        self,
        repository: MatchmakingAnalysisRepositoryInterface,
        gateway: MatchmakingGateway,
        transformer: MatchmakingAnalysisTransformer,
        db: AsyncSession,
    ):
        """Initialize service with dependencies.

        :param repository: Data access repository
        :param gateway: External API gateway
        :param transformer: Data transformer
        :param db: Database session for transaction management
        """
        self.repository = repository
        self.gateway = gateway
        self.transformer = transformer
        self.db = db

        # Initialize analysis components
        self.match_processor = MatchDataProcessor()
        self.fairness_calculator = FairnessCalculator()
        self.orchestrator = AnalysisOrchestrator(
            repository=repository,
            gateway=gateway,
            match_processor=self.match_processor,
            fairness_calculator=self.fairness_calculator,
            parameter_schema=AnalysisParameters,
        )

    @service_error_handler("MatchmakingAnalysisService")
    async def start_analysis(
        self, request: MatchmakingAnalysisCreate
    ) -> MatchmakingAnalysisResponse:
        """Start a new matchmaking analysis with transaction management.

        Creates the analysis job record and returns immediately.
        Background execution should be scheduled by the caller (e.g., via BackgroundTasks).

        :param request: Analysis creation request
        :returns: Analysis response schema with job ID for status polling
        :raises ServiceException: If analysis creation fails
        """
        try:
            # Create analysis job through repository (no commit yet)
            job_orm = await self.repository.create_analysis(request)

            # Commit transaction
            await self.db.commit()

            logger.info(
                "analysis_created",
                analysis_id=job_orm.id,
                user_id=job_orm.user_id,
                parameters=job_orm.parameters,
            )

            # Transform to response
            response = self.transformer.orm_to_response(job_orm)

            return response

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "analysis_start_failed",
                user_id=request.user_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ServiceException(
                message=f"Failed to start analysis: {str(e)}",
                service="MatchmakingAnalysisService",
                operation="start_analysis",
                original_error=e,
            )

    @service_error_handler("MatchmakingAnalysisService")
    async def get_analysis_status(
        self, analysis_id: str
    ) -> Optional[MatchmakingAnalysisResponse]:
        """Get current analysis status (read-only, no transaction).

        :param analysis_id: Analysis job ID
        :returns: Analysis response or None if not found
        """
        job_orm = await self.repository.get_analysis_by_id(analysis_id)
        if not job_orm:
            logger.warning("analysis_not_found", analysis_id=analysis_id)
            return None

        return self.transformer.orm_to_response(job_orm)

    @service_error_handler("MatchmakingAnalysisService")
    async def get_user_analyses(
        self, user_id: str, limit: int = 50
    ) -> List[MatchmakingAnalysisResponse]:
        """Get user's analysis history (read-only, no transaction).

        :param user_id: User ID
        :param limit: Maximum number of results
        :returns: List of analysis responses
        """
        jobs = await self.repository.get_user_analyses(user_id, limit)

        logger.debug(
            "user_analyses_retrieved",
            user_id=user_id,
            count=len(jobs),
        )

        return [self.transformer.orm_to_response(job) for job in jobs]

    async def execute_background_analysis(self, analysis_id: str) -> None:
        """Execute the actual matchmaking analysis in background.

        This method will be called by background job system.
        Transaction management is handled within orchestrator.

        :param analysis_id: Analysis job ID
        """
        try:
            await self.orchestrator.execute_analysis(analysis_id)
            await self.db.commit()

            logger.info(
                "background_analysis_completed",
                analysis_id=analysis_id,
            )

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "background_analysis_failed",
                analysis_id=analysis_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    