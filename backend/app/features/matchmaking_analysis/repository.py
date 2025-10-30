from typing import Protocol, List, Optional, Dict, Any
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.features.matchmaking_analysis.orm_models import JobExecutionORM
from app.features.matchmaking_analysis.schemas import MatchmakingAnalysisCreate
from app.core.enums import JobStatus


class MatchmakingAnalysisRepositoryInterface(Protocol):
    """Repository interface for matchmaking analysis data operations"""

    async def create_analysis(
        self, analysis: MatchmakingAnalysisCreate
    ) -> JobExecutionORM:
        """Create a new matchmaking analysis job"""
        ...

    async def get_analysis_by_id(self, analysis_id: str) -> Optional[JobExecutionORM]:
        """Retrieve analysis by ID"""
        ...

    async def update_analysis_status(self, analysis_id: str, status: JobStatus) -> None:
        """Update analysis status"""
        ...

    async def get_user_analyses(
        self, user_id: str, limit: int = 50
    ) -> List[JobExecutionORM]:
        """Get user's analysis history"""
        ...

    async def save_analysis_results(
        self, analysis_id: str, results: Dict[str, Any]
    ) -> None:
        """Save analysis results"""
        ...


class SQLAlchemyMatchmakingAnalysisRepository:
    """SQLAlchemy implementation of matchmaking analysis repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_analysis(
        self, analysis: MatchmakingAnalysisCreate
    ) -> JobExecutionORM:
        """Create a new matchmaking analysis job"""
        job = JobExecutionORM(
            user_id=analysis.user_id,
            job_type="matchmaking_analysis",
            status=JobStatus.PENDING,
            parameters=analysis.parameters or {},
            created_at=datetime.now(timezone.utc),
        )

        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_analysis_by_id(self, analysis_id: str) -> Optional[JobExecutionORM]:
        """Retrieve analysis by ID"""
        stmt = select(JobExecutionORM).where(JobExecutionORM.id == analysis_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_analysis_status(self, analysis_id: str, status: JobStatus) -> None:
        """Update analysis status"""
        stmt = (
            update(JobExecutionORM)
            .where(JobExecutionORM.id == analysis_id)
            .values(status=status.value)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def get_user_analyses(
        self, user_id: str, limit: int = 50
    ) -> List[JobExecutionORM]:
        """Get user's analysis history"""
        stmt = (
            select(JobExecutionORM)
            .where(JobExecutionORM.user_id == user_id)
            .where(JobExecutionORM.job_type == "matchmaking_analysis")
            .order_by(JobExecutionORM.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def save_analysis_results(
        self, analysis_id: str, results: Dict[str, Any]
    ) -> None:
        """Save analysis results"""
        stmt = (
            update(JobExecutionORM)
            .where(JobExecutionORM.id == analysis_id)
            .values(
                result=results,
                winrate=results.get("winrate"),
                avg_rank_difference=results.get("avg_rank_difference"),
                fairness_score=results.get("fairness_score"),
                matches_analyzed=results.get("matches_analyzed", 0),
                completed_at=datetime.now(timezone.utc),
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()
