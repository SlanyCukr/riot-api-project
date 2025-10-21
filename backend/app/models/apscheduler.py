"""APScheduler database model.

This table is used by APScheduler to store job state. We define it in SQLAlchemy
so Alembic can manage schema changes, but APScheduler handles the data.
"""

from sqlalchemy import String, Float, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class APSchedulerJob(Base):  # noqa: vulture
    """APScheduler job state table.

    This table is managed by the APScheduler library for job persistence.
    The schema is defined here so Alembic can track and migrate it.
    """

    __tablename__ = "apscheduler_jobs"
    __table_args__ = {
        "schema": "app",
        "info": {
            # Prevent Alembic autogenerate from trying to manage this table
            "skip_autogenerate": True,
        },
    }

    id: Mapped[str] = mapped_column(
        String(191),
        primary_key=True,
        comment="Unique job identifier",
    )

    next_run_time: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        index=True,
        comment="Next scheduled run time (Unix timestamp)",
    )

    job_state: Mapped[bytes] = mapped_column(  # noqa: vulture
        LargeBinary,
        nullable=False,
        comment="Serialized job state",
    )

    def __repr__(self) -> str:
        """Return string representation of the APScheduler job."""
        return f"<APSchedulerJob(id='{self.id}', next_run_time={self.next_run_time})>"
