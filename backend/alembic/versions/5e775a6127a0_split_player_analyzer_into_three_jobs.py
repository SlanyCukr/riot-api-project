"""split player analyzer into three jobs

Revision ID: 5e775a6127a0
Revises: f3d1e5fc09c5
Create Date: 2025-10-20 14:36:13.552569

"""

import os
import json
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "5e775a6127a0"
down_revision: Union[str, Sequence[str], None] = "f3d1e5fc09c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Split Player Analyzer into three separate jobs."""

    env = os.getenv("ENVIRONMENT", "dev").lower()

    # Delete old Player Analyzer
    op.execute("""
        DELETE FROM app.job_configurations
        WHERE job_type = 'PLAYER_ANALYZER'
    """)

    if env == "dev":
        # Development configuration - conservative API usage
        create_dev_jobs()
    else:
        # Production configuration - aggressive for throughput
        create_prod_jobs()


def create_dev_jobs() -> None:
    """Create job configurations for development environment."""
    # Match Fetcher - 30 min interval, conservative
    op.execute(  # nosec B608
        f"""
        INSERT INTO app.job_configurations
        (job_type, name, schedule, is_active, config_json, created_at, updated_at)
        VALUES (
            'MATCH_FETCHER', 'Match Fetcher', 'interval:1800', true,
            '{
        json.dumps(
            {
                "interval_seconds": 1800,
                "timeout_seconds": 300,
                "discovered_players_per_run": 2,
                "matches_per_player_per_run": 5,
                "target_matches_per_player": 50,
            }
        )
    }'::jsonb, NOW(), NOW()
        )
        ON CONFLICT (job_type) DO UPDATE SET
            schedule = EXCLUDED.schedule, config_json = EXCLUDED.config_json, updated_at = NOW()
    """)

    # Smurf Analyzer - 5 min interval, no API calls
    op.execute(  # nosec B608
        f"""
        INSERT INTO app.job_configurations
        (job_type, name, schedule, is_active, config_json, created_at, updated_at)
        VALUES (
            'SMURF_ANALYZER', 'Smurf Analyzer', 'interval:300', true,
            '{
        json.dumps(
            {
                "interval_seconds": 300,
                "timeout_seconds": 60,
                "unanalyzed_players_per_run": 50,
                "min_matches_required": 20,
            }
        )
    }'::jsonb, NOW(), NOW()
        )
        ON CONFLICT (job_type) DO UPDATE SET
            schedule = EXCLUDED.schedule, config_json = EXCLUDED.config_json, updated_at = NOW()
    """)

    # Ban Checker - daily
    op.execute(  # nosec B608
        f"""
        INSERT INTO app.job_configurations
        (job_type, name, schedule, is_active, config_json, created_at, updated_at)
        VALUES (
            'BAN_CHECKER', 'Ban Checker', 'interval:86400', true,
            '{
        json.dumps(
            {
                "interval_seconds": 86400,
                "timeout_seconds": 120,
                "ban_check_days": 14,
                "max_checks_per_run": 10,
            }
        )
    }'::jsonb, NOW(), NOW()
        )
        ON CONFLICT (job_type) DO UPDATE SET
            schedule = EXCLUDED.schedule, config_json = EXCLUDED.config_json, updated_at = NOW()
    """)


def create_prod_jobs() -> None:
    """Create job configurations for production environment."""
    # Match Fetcher - 2 min interval, tuned for ~80 API calls per 2min
    # 100 req/2min limit - targeting 80 calls = 8 players × 10 matches
    op.execute(  # nosec B608
        f"""
        INSERT INTO app.job_configurations
        (job_type, name, schedule, is_active, config_json, created_at, updated_at)
        VALUES (
            'MATCH_FETCHER', 'Match Fetcher', 'interval:120', true,
            '{
        json.dumps(
            {
                "interval_seconds": 120,
                "timeout_seconds": 90,
                "discovered_players_per_run": 8,
                "matches_per_player_per_run": 10,
                "target_matches_per_player": 100,
            }
        )
    }'::jsonb, NOW(), NOW()
        )
        ON CONFLICT (job_type) DO UPDATE SET
            schedule = EXCLUDED.schedule, config_json = EXCLUDED.config_json, updated_at = NOW()
    """)

    # Smurf Analyzer - 2 min interval, no API calls
    op.execute(  # nosec B608
        f"""
        INSERT INTO app.job_configurations
        (job_type, name, schedule, is_active, config_json, created_at, updated_at)
        VALUES (
            'SMURF_ANALYZER', 'Smurf Analyzer', 'interval:120', true,
            '{
        json.dumps(
            {
                "interval_seconds": 120,
                "timeout_seconds": 60,
                "unanalyzed_players_per_run": 100,
                "min_matches_required": 20,
            }
        )
    }'::jsonb, NOW(), NOW()
        )
        ON CONFLICT (job_type) DO UPDATE SET
            schedule = EXCLUDED.schedule, config_json = EXCLUDED.config_json, updated_at = NOW()
    """)

    # Ban Checker - every 8 hours, limited API calls
    op.execute(  # nosec B608
        f"""
        INSERT INTO app.job_configurations
        (job_type, name, schedule, is_active, config_json, created_at, updated_at)
        VALUES (
            'BAN_CHECKER', 'Ban Checker', 'interval:28800', true,
            '{
        json.dumps(
            {
                "interval_seconds": 28800,
                "timeout_seconds": 120,
                "ban_check_days": 3,
                "max_checks_per_run": 20,
            }
        )
    }'::jsonb, NOW(), NOW()
        )
        ON CONFLICT (job_type) DO UPDATE SET
            schedule = EXCLUDED.schedule, config_json = EXCLUDED.config_json, updated_at = NOW()
    """)


def downgrade() -> None:
    """Remove new jobs."""
    op.execute("""
        DELETE FROM app.job_configurations
        WHERE job_type IN ('MATCH_FETCHER', 'SMURF_ANALYZER', 'BAN_CHECKER')
    """)
