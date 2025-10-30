from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import String, Text, DateTime, Float, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base

from app.features.jobs.models import JobStatus

Base = declarative_base()


class JobExecutionORM(Base):
    """Enhanced JobExecution model with rich domain methods"""

    __tablename__ = "job_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        String(20), nullable=False, default=JobStatus.PENDING
    )
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Analysis-specific fields (existing)
    matches_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    winrate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_rank_difference: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fairness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def start_analysis(self) -> None:
        """Initialize analysis and set status to RUNNING"""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.utcnow()

    def calculate_progress(self, total_matches: int, processed_matches: int) -> float:
        """Calculate analysis completion percentage"""
        if total_matches == 0:
            return 0.0
        progress = (processed_matches / total_matches) * 100
        return min(100.0, progress)

    def handle_failure(self, error_message: str) -> None:
        """Handle analysis failure with proper error tracking"""
        self.status = JobStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()

    def get_analysis_results(self) -> Dict[str, Any]:
        """Retrieve computed analysis metrics"""
        return {
            "matches_analyzed": self.matches_analyzed,
            "winrate": self.winrate,
            "avg_rank_difference": self.avg_rank_difference,
            "fairness_score": self.fairness_score,
            "result": self.result,
        }
