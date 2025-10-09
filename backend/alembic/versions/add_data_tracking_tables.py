"""Add data tracking tables for intelligent data management

Revision ID: add_data_tracking_tables
Revises:
Create Date: 2025-06-18 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "81596165fa0c"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create data_tracking table
    op.create_table(
        "data_tracking",
        sa.Column(
            "id", sa.Integer(), nullable=False, comment="Auto-incrementing primary key"
        ),
        sa.Column(
            "data_type",
            sa.String(length=50),
            nullable=False,
            comment="Type of data (account, summoner, match, rank, etc.)",
        ),
        sa.Column(
            "identifier",
            sa.String(length=255),
            nullable=False,
            comment="Unique identifier for the data (PUUID, match ID, etc.)",
        ),
        sa.Column(
            "last_fetched",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Last time data was fetched from Riot API",
        ),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Last time this record was updated",
        ),
        sa.Column(
            "fetch_count",
            sa.Integer(),
            nullable=False,
            default=1,
            comment="Number of times this data has been fetched",
        ),
        sa.Column(
            "hit_count",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="Number of times this data was served from database",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            default=True,
            comment="Whether this data is still actively tracked",
        ),
        sa.Column(
            "last_hit",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last time this data was requested",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When this tracking record was created",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When this tracking record was last updated",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "data_type", "identifier", name="uq_data_tracking_type_identifier"
        ),
        sa.CheckConstraint(
            "fetch_count >= 0", name="ck_data_tracking_fetch_count_positive"
        ),
        sa.CheckConstraint(
            "hit_count >= 0", name="ck_data_tracking_hit_count_positive"
        ),
        comment="Tracks freshness and usage patterns for Riot API data",
    )

    # Create indexes for data_tracking
    op.create_index("ix_data_tracking_type", "data_tracking", ["data_type"])
    op.create_index("ix_data_tracking_identifier", "data_tracking", ["identifier"])
    op.create_index(
        "ix_data_tracking_type_fetched", "data_tracking", ["data_type", "last_fetched"]
    )
    op.create_index(
        "ix_data_tracking_active_hit", "data_tracking", ["is_active", "last_hit"]
    )

    # Create api_request_queue table
    op.create_table(
        "api_request_queue",
        sa.Column(
            "id", sa.Integer(), nullable=False, comment="Auto-incrementing primary key"
        ),
        sa.Column(
            "data_type",
            sa.String(length=50),
            nullable=False,
            comment="Type of data to fetch",
        ),
        sa.Column(
            "identifier",
            sa.String(length=255),
            nullable=False,
            comment="Identifier for the data to fetch",
        ),
        sa.Column(
            "priority",
            sa.String(length=20),
            nullable=False,
            default="normal",
            comment="Priority level (low, normal, high, urgent)",
        ),
        sa.Column(
            "scheduled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            default=sa.text("now()"),
            comment="When this request should be processed",
        ),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="Number of times this request has been retried",
        ),
        sa.Column(
            "max_retries",
            sa.Integer(),
            nullable=False,
            default=3,
            comment="Maximum number of retries allowed",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            default="pending",
            comment="Request status (pending, processing, completed, failed, cancelled)",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error message if request failed",
        ),
        sa.Column(
            "last_error_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the last error occurred",
        ),
        sa.Column(
            "request_data",
            sa.Text(),
            nullable=True,
            comment="Additional request parameters (JSON string)",
        ),
        sa.Column(
            "response_data",
            sa.Text(),
            nullable=True,
            comment="Response data for successful requests (JSON string)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When this request was queued",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When this request was last updated",
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When this request was processed",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "retry_count >= 0", name="ck_api_request_queue_retry_count_positive"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')",
            name="ck_api_request_queue_status_valid",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_api_request_queue_priority_valid",
        ),
        comment="Queue system for rate-limited API requests",
    )

    # Create indexes for api_request_queue
    op.create_index("ix_api_request_queue_type", "api_request_queue", ["data_type"])
    op.create_index(
        "ix_api_request_queue_identifier", "api_request_queue", ["identifier"]
    )
    op.create_index("ix_api_request_queue_priority", "api_request_queue", ["priority"])
    op.create_index("ix_api_request_queue_status", "api_request_queue", ["status"])
    op.create_index(
        "ix_api_request_queue_scheduled", "api_request_queue", ["scheduled_at"]
    )
    op.create_index(
        "ix_api_request_queue_status_priority",
        "api_request_queue",
        ["status", "priority", "scheduled_at"],
    )
    op.create_index(
        "ix_api_request_queue_scheduled_status",
        "api_request_queue",
        ["scheduled_at", "status"],
    )
    op.create_index("ix_api_request_queue_created", "api_request_queue", ["created_at"])

    # Create rate_limit_log table
    op.create_table(
        "rate_limit_log",
        sa.Column(
            "id", sa.Integer(), nullable=False, comment="Auto-incrementing primary key"
        ),
        sa.Column(
            "limit_type",
            sa.String(length=20),
            nullable=False,
            comment="Type of rate limit (app, method, service)",
        ),
        sa.Column(
            "endpoint",
            sa.String(length=255),
            nullable=True,
            comment="API endpoint that triggered the rate limit",
        ),
        sa.Column(
            "limit_count",
            sa.Integer(),
            nullable=True,
            comment="Rate limit count (requests allowed)",
        ),
        sa.Column(
            "limit_window",
            sa.Integer(),
            nullable=True,
            comment="Rate limit window (seconds)",
        ),
        sa.Column(
            "current_usage",
            sa.Integer(),
            nullable=True,
            comment="Current usage when rate limit was hit",
        ),
        sa.Column(
            "retry_after",
            sa.Integer(),
            nullable=True,
            comment="Retry-After header value in seconds",
        ),
        sa.Column(
            "request_data",
            sa.Text(),
            nullable=True,
            comment="Context about the request that hit the limit",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When this rate limit event occurred",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "limit_count > 0", name="ck_rate_limit_log_limit_count_positive"
        ),
        sa.CheckConstraint(
            "limit_window > 0", name="ck_rate_limit_log_limit_window_positive"
        ),
        sa.CheckConstraint(
            "current_usage >= 0", name="ck_rate_limit_log_current_usage_positive"
        ),
        sa.CheckConstraint(
            "retry_after >= 0", name="ck_rate_limit_log_retry_after_positive"
        ),
        comment="Logs rate limit events for analysis and optimization",
    )

    # Create indexes for rate_limit_log
    op.create_index("ix_rate_limit_log_type", "rate_limit_log", ["limit_type"])
    op.create_index("ix_rate_limit_log_endpoint", "rate_limit_log", ["endpoint"])
    op.create_index(
        "ix_rate_limit_log_type_created", "rate_limit_log", ["limit_type", "created_at"]
    )
    op.create_index("ix_rate_limit_log_created", "rate_limit_log", ["created_at"])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index("ix_rate_limit_log_created", table_name="rate_limit_log")
    op.drop_index("ix_rate_limit_log_type_created", table_name="rate_limit_log")
    op.drop_index("ix_rate_limit_log_endpoint", table_name="rate_limit_log")
    op.drop_index("ix_rate_limit_log_type", table_name="rate_limit_log")

    op.drop_index("ix_api_request_queue_created", table_name="api_request_queue")
    op.drop_index(
        "ix_api_request_queue_scheduled_status", table_name="api_request_queue"
    )
    op.drop_index(
        "ix_api_request_queue_status_priority", table_name="api_request_queue"
    )
    op.drop_index("ix_api_request_queue_scheduled", table_name="api_request_queue")
    op.drop_index("ix_api_request_queue_status", table_name="api_request_queue")
    op.drop_index("ix_api_request_queue_priority", table_name="api_request_queue")
    op.drop_index("ix_api_request_queue_identifier", table_name="api_request_queue")
    op.drop_index("ix_api_request_queue_type", table_name="api_request_queue")

    op.drop_index("ix_data_tracking_active_hit", table_name="data_tracking")
    op.drop_index("ix_data_tracking_type_fetched", table_name="data_tracking")
    op.drop_index("ix_data_tracking_identifier", table_name="data_tracking")
    op.drop_index("ix_data_tracking_type", table_name="data_tracking")

    # Drop tables
    op.drop_table("rate_limit_log")
    op.drop_table("api_request_queue")
    op.drop_table("data_tracking")
