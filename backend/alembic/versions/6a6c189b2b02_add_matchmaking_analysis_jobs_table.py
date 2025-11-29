"""Add matchmaking_analysis_jobs table

Revision ID: 6a6c189b2b02
Revises: 2438ef1ce370
Create Date: 2025-11-02 21:19:40.293131

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a6c189b2b02'
down_revision: Union[str, Sequence[str], None] = '2438ef1ce370'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create matchmaking_analysis_jobs table
    op.create_table('matchmaking_analysis_jobs',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('job_type', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('parameters', sa.JSON(), nullable=True),
    sa.Column('result', sa.JSON(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('progress', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('matches_analyzed', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('winrate', sa.Float(), nullable=True),
    sa.Column('avg_rank_difference', sa.Float(), nullable=True),
    sa.Column('fairness_score', sa.Float(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.CheckConstraint('progress >= 0.0 AND progress <= 100.0', name='check_progress_range'),
    sa.CheckConstraint('winrate >= 0.0 AND winrate <= 1.0', name='check_winrate_range'),
    sa.CheckConstraint('avg_rank_difference >= 0.0', name='check_rank_difference_positive'),
    sa.CheckConstraint('fairness_score >= 0.0 AND fairness_score <= 1.0', name='check_fairness_score_range')
    )
    op.create_index('ix_matchmaking_analysis_jobs_user_id', 'matchmaking_analysis_jobs', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_matchmaking_analysis_jobs_user_id', table_name='matchmaking_analysis_jobs')
    op.drop_table('matchmaking_analysis_jobs')
