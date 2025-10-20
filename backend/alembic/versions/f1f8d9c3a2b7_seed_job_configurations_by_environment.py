"""Seed job configurations by environment

Revision ID: f1f8d9c3a2b7
Revises: eee6cc88f8fb
Create Date: 2025-10-19 20:56:00.000000

"""

import os
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f1f8d9c3a2b7"
down_revision: Union[str, Sequence[str], None] = "eee6cc88f8fb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update existing job configurations based on current environment."""
    # Get current environment from ENVIRONMENT variable
    env = os.getenv("ENVIRONMENT", "dev").lower()

    # Update existing job configurations instead of creating new ones
    # This prevents duplicate configurations in production

    # Update Tracked Player Updater
    if env == "dev":
        # Development settings (conservative)
        op.execute(  # nosec B608
            f"""
            UPDATE job_configurations
            SET schedule = 'interval:600',
                config_json = '{
                json.dumps(
                    {
                        "interval_seconds": 600,
                        "timeout_seconds": 300,
                        "max_tracked_players": 3,
                        "max_new_matches_per_player": 5,
                    }
                )
            }'::jsonb
            WHERE job_type = 'TRACKED_PLAYER_UPDATER'
        """
        )

    else:  # production
        # Production settings (full performance)
        op.execute(  # nosec B608
            f"""
            UPDATE job_configurations
            SET schedule = 'interval:120',
                config_json = '{
                json.dumps(
                    {
                        "interval_seconds": 120,
                        "timeout_seconds": 90,
                        "max_tracked_players": 10,
                        "max_new_matches_per_player": 50,
                    }
                )
            }'::jsonb
            WHERE job_type = 'TRACKED_PLAYER_UPDATER'
        """
        )


def downgrade() -> None:
    """Remove seeded job configurations."""
    # Remove all job configurations that were seeded by this migration
    op.execute(
        sa.text(
            "DELETE FROM job_configurations WHERE name LIKE '% - Dev' OR name LIKE '% - Production'"
        )
    )
