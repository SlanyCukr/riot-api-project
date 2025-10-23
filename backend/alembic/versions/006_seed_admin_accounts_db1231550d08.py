"""seed_admin_accounts

Revision ID: db1231550d08
Revises: 3e390f28278a
Create Date: 2025-10-23 03:17:40.798453

Seeds two admin accounts with hashed passwords using Argon2id.
"""

from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from passlib.context import CryptContext


# revision identifiers, used by Alembic.
revision: str = "db1231550d08"
down_revision: Union[str, Sequence[str], None] = "3e390f28278a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Password hashing context using Argon2id
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def upgrade() -> None:
    """Seed admin accounts."""

    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    # Hash passwords
    password1 = "Posote19$$"
    password2 = "606361611Aa."

    hash1 = pwd_context.hash(password1)
    hash2 = pwd_context.hash(password2)

    # Insert admin accounts
    conn.execute(
        sa.text(
            """
            INSERT INTO auth.users (email, password_hash, display_name, is_active, is_admin, email_verified, email_verified_at, created_at, updated_at)
            VALUES
                (:email1, :hash1, :name1, true, true, true, :now, :now, :now),
                (:email2, :hash2, :name2, true, true, true, :now, :now, :now)
        """
        ),
        {
            "email1": "mat.kadlec@email.cz",
            "hash1": hash1,
            "name1": "Matěj Kadlec",
            "email2": "marek.hovadik@seznam.cz",
            "hash2": hash2,
            "name2": "Marek Hovadík",
            "now": now,
        },
    )

    print("Admin accounts seeded successfully!")
    print("  - mat.kadlec@email.cz (Matěj Kadlec)")
    print("  - marek.hovadik@seznam.cz (Marek Hovadík)")


def downgrade() -> None:
    """Remove seeded admin accounts."""

    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            DELETE FROM auth.users
            WHERE email IN ('mat.kadlec@email.cz', 'marek.hovadik@seznam.cz')
        """
        )
    )

    print("Admin accounts removed!")
