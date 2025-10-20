"""update job_type enum values

Revision ID: 2d051c0a629b
Revises: 5e775a6127a0
Create Date: 2025-10-20 14:40:08.865520

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2d051c0a629b"
down_revision: Union[str, Sequence[str], None] = "f1f8d9c3a2b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new job type enum values."""
    # Add new enum values (keeping PLAYER_ANALYZER for backward compat during migration)
    # Note: Each ALTER TYPE must be in its own transaction for PostgreSQL
    op.execute("COMMIT")
    op.execute("ALTER TYPE app.job_type_enum ADD VALUE IF NOT EXISTS 'MATCH_FETCHER'")
    op.execute("COMMIT")
    op.execute("ALTER TYPE app.job_type_enum ADD VALUE IF NOT EXISTS 'SMURF_ANALYZER'")
    op.execute("COMMIT")
    op.execute("ALTER TYPE app.job_type_enum ADD VALUE IF NOT EXISTS 'BAN_CHECKER'")
    op.execute("COMMIT")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: Cannot remove enum values in PostgreSQL
    pass
