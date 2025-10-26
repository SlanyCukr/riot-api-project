"""drop_old_smurf_detections_table

Revision ID: 2438ef1ce370
Revises: 1b9da77b35df
Create Date: 2025-10-26 17:22:37.714725

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2438ef1ce370"
down_revision: Union[str, Sequence[str], None] = "1b9da77b35df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop obsolete smurf_detections table.

    The smurf_detections table was replaced by player_analysis in migration 006.
    In production, this table was manually renamed to player_analysis.
    In development, both tables exist due to migration history.
    This migration removes the old table to align all environments.
    """
    # Drop the old smurf_detections table if it exists
    # Production: table doesn't exist (was renamed) - IF EXISTS handles this
    # Development: table exists but is empty - safe to drop
    op.execute("DROP TABLE IF EXISTS core.smurf_detections CASCADE")


def downgrade() -> None:
    """Downgrade not supported.

    Cannot recreate smurf_detections as it was an obsolete duplicate.
    Data migration to player_analysis already completed.
    """
    # Downgrade not supported - the old table structure is deprecated
    pass
