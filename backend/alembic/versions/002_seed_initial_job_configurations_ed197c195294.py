"""002_seed_initial_job_configurations

Revision ID: ed197c195294
Revises: 3cf0af6dff87
Create Date: 2025-10-21 11:51:43.519769

"""

import os
import json
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "ed197c195294"
down_revision: Union[str, Sequence[str], None] = "3cf0af6dff87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed initial job configurations based on environment."""

    env = os.getenv("ENVIRONMENT", "dev").lower()

    if env == "dev":
        create_dev_jobs()
    else:
        create_prod_jobs()


def create_dev_jobs() -> None:
    """Create job configurations for development environment."""

    # Tracked Player Updater - 10 min interval, conservative
    op.execute(  # nosec B608
        f"""
        INSERT INTO app.job_configurations
        (job_type, name, schedule, is_active, config_json, created_at, updated_at)
        VALUES (
            'TRACKED_PLAYER_UPDATER', 'Tracked Player Updater', 'interval:600', true,
            '{
            json.dumps(
                {
                    "interval_seconds": 600,
                    "timeout_seconds": 300,
                    "max_tracked_players": 3,
                    "max_new_matches_per_player": 5,
                }
            )
        }'::jsonb, NOW(), NOW()
        )
        ON CONFLICT (name) DO UPDATE SET
            job_type = EXCLUDED.job_type,
            schedule = EXCLUDED.schedule,
            config_json = EXCLUDED.config_json,
            updated_at = NOW()
    """
    )

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
        ON CONFLICT (name) DO UPDATE SET
            job_type = EXCLUDED.job_type,
            schedule = EXCLUDED.schedule,
            config_json = EXCLUDED.config_json,
            updated_at = NOW()
    """
    )

    # Player Analyzer - 5 min interval, no API calls
    op.execute(  # nosec B608
        f"""
        INSERT INTO app.job_configurations
        (job_type, name, schedule, is_active, config_json, created_at, updated_at)
        VALUES (
            'PLAYER_ANALYZER', 'Player Analyzer', 'interval:300', true,
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
        ON CONFLICT (name) DO UPDATE SET
            job_type = EXCLUDED.job_type,
            schedule = EXCLUDED.schedule,
            config_json = EXCLUDED.config_json,
            updated_at = NOW()
    """
    )

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
        ON CONFLICT (name) DO UPDATE SET
            job_type = EXCLUDED.job_type,
            schedule = EXCLUDED.schedule,
            config_json = EXCLUDED.config_json,
            updated_at = NOW()
    """
    )


def create_prod_jobs() -> None:
    """Create job configurations for production environment."""

    # Tracked Player Updater - 2 min interval, aggressive
    op.execute(  # nosec B608
        f"""
        INSERT INTO app.job_configurations
        (job_type, name, schedule, is_active, config_json, created_at, updated_at)
        VALUES (
            'TRACKED_PLAYER_UPDATER', 'Tracked Player Updater', 'interval:120', true,
            '{
            json.dumps(
                {
                    "interval_seconds": 120,
                    "timeout_seconds": 90,
                    "max_tracked_players": 10,
                    "max_new_matches_per_player": 50,
                }
            )
        }'::jsonb, NOW(), NOW()
        )
        ON CONFLICT (name) DO UPDATE SET
            job_type = EXCLUDED.job_type,
            schedule = EXCLUDED.schedule,
            config_json = EXCLUDED.config_json,
            updated_at = NOW()
    """
    )

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
        ON CONFLICT (name) DO UPDATE SET
            job_type = EXCLUDED.job_type,
            schedule = EXCLUDED.schedule,
            config_json = EXCLUDED.config_json,
            updated_at = NOW()
    """
    )

    # Player Analyzer - 2 min interval, no API calls
    op.execute(  # nosec B608
        f"""
        INSERT INTO app.job_configurations
        (job_type, name, schedule, is_active, config_json, created_at, updated_at)
        VALUES (
            'PLAYER_ANALYZER', 'Player Analyzer', 'interval:120', true,
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
        ON CONFLICT (name) DO UPDATE SET
            job_type = EXCLUDED.job_type,
            schedule = EXCLUDED.schedule,
            config_json = EXCLUDED.config_json,
            updated_at = NOW()
    """
    )

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
        ON CONFLICT (name) DO UPDATE SET
            job_type = EXCLUDED.job_type,
            schedule = EXCLUDED.schedule,
            config_json = EXCLUDED.config_json,
            updated_at = NOW()
    """
    )


def downgrade() -> None:
    """Remove seeded job configurations."""
    op.execute("""
        DELETE FROM app.job_configurations
        WHERE job_type IN ('TRACKED_PLAYER_UPDATER', 'MATCH_FETCHER', 'PLAYER_ANALYZER', 'BAN_CHECKER')
    """)
