"""Add RATE_LIMITED status to JobStatus enum

Revision ID: eee6cc88f8fb
Revises: a4330d2a7ce6
Create Date: 2025-10-19 17:30:39.388775

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "eee6cc88f8fb"
down_revision: Union[str, Sequence[str], None] = "69dcb5a3c7f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add rate_limited value to JobStatus enum
    # Note: Must match enum value (lowercase), not the Python enum name
    op.execute("ALTER TYPE app.job_status_enum ADD VALUE IF NOT EXISTS 'rate_limited'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL doesn't support removing enum values
    # Manual intervention required if downgrade is needed
    pass
