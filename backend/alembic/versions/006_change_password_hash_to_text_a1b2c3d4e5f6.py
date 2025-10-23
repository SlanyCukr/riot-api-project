"""change_password_hash_to_text

Revision ID: a1b2c3d4e5f6
Revises: 3e390f28278a
Create Date: 2025-10-23 14:30:00.000000

Changes the password_hash column from String(255) to Text type to future-proof
against longer Argon2 hashes with different security parameters.

Argon2 hashes are typically ~90-100 characters, but using Text type ensures we
can support more secure configurations in the future without schema changes.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "3e390f28278a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change password_hash column from String(255) to Text."""
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=False,
        schema="auth",
    )


def downgrade() -> None:
    """Revert password_hash column from Text to String(255)."""
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False,
        schema="auth",
    )
