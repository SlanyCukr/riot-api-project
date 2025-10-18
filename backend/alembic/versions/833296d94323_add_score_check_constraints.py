"""add_score_check_constraints

Revision ID: 833296d94323
Revises: 6104f75cdfe9
Create Date: 2025-10-18 16:49:09.974406

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "833296d94323"
down_revision: Union[str, Sequence[str], None] = "6104f75cdfe9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add CHECK constraints for score fields."""
    # Add CHECK constraints to ensure all score fields are between 0.0 and 1.0
    score_fields = [
        "smurf_score",
        "win_rate_score",
        "kda_score",
        "account_level_score",
        "rank_discrepancy_score",
        "rank_progression_score",
        "win_rate_trend_score",
        "performance_consistency_score",
        "performance_trends_score",
        "role_performance_score",
    ]

    for field in score_fields:
        constraint_name = f"check_{field}_range"
        op.create_check_constraint(
            constraint_name,
            "smurf_detections",
            sa.text(f"{field} IS NULL OR ({field} >= 0.0 AND {field} <= 1.0)"),
        )


def downgrade() -> None:
    """Downgrade schema - remove CHECK constraints for score fields."""
    # Remove CHECK constraints
    score_fields = [
        "smurf_score",
        "win_rate_score",
        "kda_score",
        "account_level_score",
        "rank_discrepancy_score",
        "rank_progression_score",
        "win_rate_trend_score",
        "performance_consistency_score",
        "performance_trends_score",
        "role_performance_score",
    ]

    for field in score_fields:
        constraint_name = f"check_{field}_range"
        op.drop_constraint(constraint_name, "smurf_detections", type_="check")
