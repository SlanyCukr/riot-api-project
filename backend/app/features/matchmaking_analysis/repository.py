"""Repository pattern implementation for matchmaking analysis feature."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.features.matchmaking_analysis.orm_models import JobExecutionORM
from app.features.matchmaking_analysis.schemas import MatchmakingAnalysisCreate
from app.core.enums import JobStatus

logger = structlog.get_logger(__name__)


class MatchmakingAnalysisRepositoryInterface(ABC):
    """Repository interface for matchmaking analysis data operations.

    Defines contract for data access operations following Repository Pattern.
    Enables mocking and potential swap of implementations.
    """

    @property
    @abstractmethod
    def db(self) -> AsyncSession:
        """Get the database session.

        :returns: AsyncSession instance
        """
        pass

    @abstractmethod
    async def create_analysis(
        self, analysis: MatchmakingAnalysisCreate
    ) -> JobExecutionORM:
        """Create a new matchmaking analysis job.

        :param analysis: Analysis creation schema
        :returns: Created ORM instance (not committed)
        """
        pass

    @abstractmethod
    async def get_analysis_by_id(
        self, analysis_id: str, for_update: bool = False
    ) -> Optional[JobExecutionORM]:
        """Retrieve analysis by ID with optional row-level lock.

        :param analysis_id: Analysis job ID
        :param for_update: If True, acquire row-level lock (FOR UPDATE)
        :returns: JobExecutionORM if found, None otherwise
        """
        pass

    @abstractmethod
    async def update_analysis_status(
        self, analysis_id: str, status: JobStatus
    ) -> Optional[JobExecutionORM]:
        """Update analysis status.

        :param analysis_id: Analysis job ID
        :param status: New status
        :returns: Updated ORM instance or None if not found
        """
        pass

    @abstractmethod
    async def update_analysis_progress(
        self, analysis_id: str, progress: float
    ) -> Optional[JobExecutionORM]:
        """Update analysis progress percentage.

        :param analysis_id: Analysis job ID
        :param progress: Progress percentage (0.0-100.0)
        :returns: Updated ORM instance or None if not found
        """
        pass

    @abstractmethod
    async def get_user_analyses(
        self, user_id: str, limit: int = 50
    ) -> List[JobExecutionORM]:
        """Get user's analysis history.

        :param user_id: User ID
        :param limit: Maximum number of results
        :returns: List of analysis jobs
        """
        pass

    @abstractmethod
    async def save_analysis_results(
        self, analysis_id: str, results: Dict[str, Any]
    ) -> Optional[JobExecutionORM]:
        """Save analysis results.

        :param analysis_id: Analysis job ID
        :param results: Analysis results dictionary
        :returns: Updated ORM instance or None if not found
        """
        pass


class SQLAlchemyMatchmakingAnalysisRepository(MatchmakingAnalysisRepositoryInterface):
    """SQLAlchemy implementation of matchmaking analysis repository.

    IMPORTANT: Repository does NOT commit transactions.
    Service layer controls transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        :param session: Database session
        """
        self._db = session

    @property
    def db(self) -> AsyncSession:
        """Get the database session.

        :returns: AsyncSession instance
        """
        return self._db

    async def create_analysis(
        self, analysis: MatchmakingAnalysisCreate
    ) -> JobExecutionORM:
        """Create a new matchmaking analysis job (NO COMMIT).

        :param analysis: Analysis creation schema
        :returns: Created ORM instance (added to session, not committed)
        """
        job = JobExecutionORM(
            user_id=analysis.user_id,
            job_type="matchmaking_analysis",
            status=JobStatus.PENDING,
            parameters=analysis.parameters or {},
            created_at=datetime.now(timezone.utc),
        )

        self._db.add(job)
        await self._db.flush()  # Flush to get ID, but don't commit
        await self._db.refresh(job)

        logger.debug(
            "analysis_created",
            analysis_id=job.id,
            user_id=job.user_id,
        )

        return job

    async def get_analysis_by_id(
        self, analysis_id: str, for_update: bool = False
    ) -> Optional[JobExecutionORM]:
        """Retrieve analysis by ID with optional row-level lock.

        :param analysis_id: Analysis job ID
        :param for_update: If True, acquire row-level lock (FOR UPDATE)
        :returns: JobExecutionORM if found, None otherwise
        """
        stmt = select(JobExecutionORM).where(JobExecutionORM.id == analysis_id)

        if for_update:
            stmt = stmt.with_for_update()

        result = await self._db.execute(stmt)
        job = result.scalar_one_or_none()

        if job:
            logger.debug(
                "analysis_retrieved",
                analysis_id=analysis_id,
                locked=for_update,
            )
        else:
            logger.warning("analysis_not_found", analysis_id=analysis_id)

        return job

    async def update_analysis_status(
        self, analysis_id: str, status: JobStatus
    ) -> Optional[JobExecutionORM]:
        """Update analysis status with row-level locking (NO COMMIT).

        Uses pessimistic locking to prevent concurrent status updates.

        :param analysis_id: Analysis job ID
        :param status: New status
        :returns: Updated ORM instance or None if not found
        """
        # Get with row-level lock to prevent race conditions
        job = await self.get_analysis_by_id(analysis_id, for_update=True)
        if not job:
            return None

        # Validate status transition
        if not self._is_valid_status_transition(job.status, status):
            logger.warning(
                "invalid_status_transition",
                analysis_id=analysis_id,
                from_status=job.status.value,
                to_status=status.value,
            )
            # Don't update, return current state
            return job

        job.status = status

        # Set timestamps based on status
        if status == JobStatus.RUNNING and not job.started_at:
            job.started_at = datetime.now(timezone.utc)
        elif status in [JobStatus.SUCCESS, JobStatus.FAILED]:
            job.completed_at = datetime.now(timezone.utc)

        await self._db.flush()

        logger.debug(
            "analysis_status_updated",
            analysis_id=analysis_id,
            status=status.value,
        )

        return job

    def _is_valid_status_transition(
        self, from_status: JobStatus, to_status: JobStatus
    ) -> bool:
        """Validate status transition is allowed.

        Valid transitions:
        - PENDING → RUNNING, FAILED
        - RUNNING → SUCCESS, FAILED
        - SUCCESS/FAILED → (terminal, no transitions)

        :param from_status: Current status
        :param to_status: New status
        :returns: True if transition is valid
        """
        valid_transitions = {
            JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.FAILED},
            JobStatus.RUNNING: {JobStatus.SUCCESS, JobStatus.FAILED},
            JobStatus.SUCCESS: set(),  # Terminal state
            JobStatus.FAILED: set(),  # Terminal state
        }

        return to_status in valid_transitions.get(from_status, set())

    async def update_analysis_progress(
        self, analysis_id: str, progress: float
    ) -> Optional[JobExecutionORM]:
        """Update analysis progress (NO COMMIT).

        :param analysis_id: Analysis job ID
        :param progress: Progress percentage (0.0-100.0)
        :returns: Updated ORM instance or None if not found
        """
        job = await self.get_analysis_by_id(analysis_id)
        if not job:
            return None

        job.progress = max(0.0, min(100.0, progress))
        await self._db.flush()

        logger.debug(
            "analysis_progress_updated",
            analysis_id=analysis_id,
            progress=job.progress,
        )

        return job

    async def get_user_analyses(
        self, user_id: str, limit: int = 50
    ) -> List[JobExecutionORM]:
        """Get user's analysis history.

        :param user_id: User ID
        :param limit: Maximum number of results
        :returns: List of analysis jobs
        """
        stmt = (
            select(JobExecutionORM)
            .where(JobExecutionORM.user_id == user_id)
            .where(JobExecutionORM.job_type == "matchmaking_analysis")
            .order_by(JobExecutionORM.created_at.desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        jobs = list(result.scalars().all())

        logger.debug(
            "user_analyses_retrieved",
            user_id=user_id,
            count=len(jobs),
        )

        return jobs

    async def save_analysis_results(
        self, analysis_id: str, results: Dict[str, Any]
    ) -> Optional[JobExecutionORM]:
        """Save analysis results (NO COMMIT).

        :param analysis_id: Analysis job ID
        :param results: Analysis results dictionary
        :returns: Updated ORM instance or None if not found
        """
        job = await self.get_analysis_by_id(analysis_id)
        if not job:
            return None

        job.result = results
        job.winrate = results.get("winrate")
        job.avg_rank_difference = results.get("avg_rank_difference")
        job.fairness_score = results.get("fairness_score")
        job.matches_analyzed = results.get("matches_analyzed", 0)
        job.completed_at = datetime.now(timezone.utc)

        await self._db.flush()

        logger.info(
            "analysis_results_saved",
            analysis_id=analysis_id,
            matches_analyzed=job.matches_analyzed,
            fairness_score=job.fairness_score,
        )

        return job
