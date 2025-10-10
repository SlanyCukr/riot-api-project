"""Data tracking models for monitoring freshness and API usage patterns."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    Index,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from . import Base


class DataTracking(Base):
    """
    Tracks data freshness and API usage patterns for optimization.

    Records when data was last fetched and updated for monitoring.
    """

    __tablename__ = "data_tracking"

    # Primary key
    id = Column(Integer, primary_key=True, comment="Auto-incrementing primary key")

    # Data identification
    data_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of data (account, summoner, match, rank, etc.)",
    )

    identifier = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Unique identifier for the data (PUUID, match ID, etc.)",
    )

    # Timestamps
    last_fetched = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Last time data was fetched from Riot API",
    )

    last_updated = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        comment="Last time this record was updated",
    )

    # Usage statistics
    fetch_count = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Number of times this data has been fetched",
    )

    hit_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of times this data was served from database",
    )

    # Status tracking
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this data is still actively tracked",
    )

    last_hit = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time this data was requested",
    )

    # Metadata
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        comment="When this tracking record was created",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
        comment="When this tracking record was last updated",
    )

    # Relationships and constraints
    __table_args__ = (
        UniqueConstraint(
            "data_type", "identifier", name="uq_data_tracking_type_identifier"
        ),
        Index(
            "ix_data_tracking_type_fetched",
            "data_type",
            "last_fetched",
        ),
        Index(
            "ix_data_tracking_active_hit",
            "is_active",
            "last_hit",
        ),
        {
            "comment": "Tracks freshness and usage patterns for Riot API data",
        },
    )

    def __repr__(self) -> str:
        """Return string representation of the data tracking."""
        return f"<DataTracking(type={self.data_type}, id={self.identifier[:8]}...)>"

    @property
    def age_hours(self) -> float:
        """Get age of data in hours."""
        if not self.last_fetched:
            return float("inf")
        return (datetime.now(timezone.utc) - self.last_fetched).total_seconds() / 3600

    @property
    def hours_since_last_hit(self) -> Optional[float]:
        """Get hours since last hit, or None if never hit."""
        if not self.last_hit:
            return None
        return (datetime.now(timezone.utc) - self.last_hit).total_seconds() / 3600

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate (hits per fetch)."""
        if self.fetch_count == 0:
            return 0.0
        return self.hit_count / self.fetch_count


class APIRequestQueue(Base):
    """
    Queue system for API requests during rate limit periods.

    Allows intelligent batching and prioritization of API calls.
    """

    __tablename__ = "api_request_queue"

    # Primary key
    id = Column(Integer, primary_key=True, comment="Auto-incrementing primary key")

    # Request identification
    data_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of data to fetch",
    )

    identifier = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Identifier for the data to fetch",
    )

    # Priority and scheduling
    priority = Column(
        String(20),
        nullable=False,
        default="normal",
        index=True,
        comment="Priority level (low, normal, high, urgent)",
    )

    scheduled_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        index=True,
        comment="When this request should be processed",
    )

    # Retry handling
    retry_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of times this request has been retried",
    )

    max_retries = Column(
        Integer,
        nullable=False,
        default=3,
        comment="Maximum number of retries allowed",
    )

    # Status tracking
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="Request status (pending, processing, completed, failed, cancelled)",
    )

    # Error handling
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if request failed",
    )

    last_error_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the last error occurred",
    )

    # Request metadata
    request_data = Column(
        Text,
        nullable=True,
        comment="Additional request parameters (JSON string)",
    )

    response_data = Column(
        Text,
        nullable=True,
        comment="Response data for successful requests (JSON string)",
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        index=True,
        comment="When this request was queued",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
        comment="When this request was last updated",
    )

    processed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this request was processed",
    )

    # Relationships and constraints
    __table_args__ = (
        Index(
            "ix_request_queue_status_priority",
            "status",
            "priority",
            "scheduled_at",
        ),
        Index(
            "ix_request_queue_scheduled_status",
            "scheduled_at",
            "status",
        ),
        {
            "comment": "Queue system for rate-limited API requests",
        },
    )

    def __repr__(self) -> str:
        """Return string representation of the API request queue."""
        return f"<APIRequestQueue(type={self.data_type}, id={self.identifier[:8]}..., status={self.status})>"

    @property
    def can_retry(self) -> bool:
        """Check if request can be retried."""
        return self.retry_count < self.max_retries and self.status == "failed"

    @property
    def age_seconds(self) -> float:
        """Get age of request in seconds."""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()

    @property
    def is_overdue(self) -> bool:
        """Check if request is overdue for processing."""
        return datetime.now(timezone.utc) > self.scheduled_at


class RateLimitLog(Base):
    """
    Logs rate limit events for analysis and optimization.

    Helps understand usage patterns and optimize request strategies.
    """

    __tablename__ = "rate_limit_log"

    # Primary key
    id = Column(Integer, primary_key=True, comment="Auto-incrementing primary key")

    # Rate limit details
    limit_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Type of rate limit (app, method, service)",
    )

    endpoint = Column(
        String(255),
        nullable=True,
        index=True,
        comment="API endpoint that triggered the rate limit",
    )

    # Rate limit values
    limit_count = Column(
        Integer,
        nullable=True,
        comment="Rate limit count (requests allowed)",
    )

    limit_window = Column(
        Integer,
        nullable=True,
        comment="Rate limit window (seconds)",
    )

    current_usage = Column(
        Integer,
        nullable=True,
        comment="Current usage when rate limit was hit",
    )

    retry_after = Column(
        Integer,
        nullable=True,
        comment="Retry-After header value in seconds",
    )

    # Request context
    request_data = Column(
        Text,
        nullable=True,
        comment="Context about the request that hit the limit",
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        index=True,
        comment="When this rate limit event occurred",
    )

    # Relationships and constraints
    __table_args__ = (
        Index(
            "ix_rate_limit_log_type_created",
            "limit_type",
            "created_at",
        ),
        Index(
            "ix_rate_limit_log_created",
            "created_at",
        ),
        {
            "comment": "Logs rate limit events for analysis and optimization",
        },
    )

    def __repr__(self) -> str:
        """Return string representation of the rate limit log."""
        return f"<RateLimitLog(type={self.limit_type}, endpoint={self.endpoint}, retry_after={self.retry_after}s)>"


# Model aliases for convenience
DataTrackingModel = DataTracking
RequestQueueModel = APIRequestQueue
RateLimitLogModel = RateLimitLog

__all__ = [
    "DataTracking",
    "APIRequestQueue",
    "RateLimitLog",
    "DataTrackingModel",
    "RequestQueueModel",
    "RateLimitLogModel",
]
