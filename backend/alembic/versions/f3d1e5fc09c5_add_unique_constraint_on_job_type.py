"""add unique constraint on job_type

Revision ID: f3d1e5fc09c5
Revises: f1f8d9c3a2b7
Create Date: 2025-10-20 14:35:46.883812

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f3d1e5fc09c5"
down_revision: Union[str, Sequence[str], None] = "2d051c0a629b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique constraint on job_type column."""
    # Add unique constraint on job_type to enable ON CONFLICT in next migration
    op.create_unique_constraint(
        "uq_job_configurations_job_type",
        "job_configurations",
        ["job_type"],
        schema="app",
    )


def downgrade() -> None:
    """Remove unique constraint on job_type column."""
    op.drop_constraint(
        "uq_job_configurations_job_type",
        "job_configurations",
        schema="app",
        type_="unique",
    )
