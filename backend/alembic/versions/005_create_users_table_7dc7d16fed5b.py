"""Create users table

Revision ID: 7dc7d16fed5b
Revises: 03230a19b98b
Create Date: 2025-10-23 13:46:34.736530

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7dc7d16fed5b"
down_revision: Union[str, Sequence[str], None] = "03230a19b98b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table in auth schema with TEXT password_hash."""

    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
            comment="Auto-incrementing primary key",
        ),
        sa.Column(
            "email",
            sa.String(length=255),
            nullable=False,
            comment="User email address (unique)",
        ),
        sa.Column(
            "password_hash",
            sa.Text(),  # ✅ TEXT type from the start - no length limit
            nullable=False,
            comment="Hashed password using Argon2id",
        ),
        sa.Column(
            "display_name",
            sa.String(length=128),
            nullable=False,
            comment="Display name shown in UI",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether the account is active (not disabled)",
        ),
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether the user has admin privileges",
        ),
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether the email has been verified",
        ),
        sa.Column(
            "email_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the email was verified",
        ),
        sa.Column(
            "last_login",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the user last logged in",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="When this user account was created",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="When this user account was last updated",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        schema="auth",
    )

    # Create indexes
    op.create_index(
        op.f("ix_users_email"), "users", ["email"], unique=False, schema="auth"
    )
    op.create_index(
        op.f("ix_users_is_active"), "users", ["is_active"], unique=False, schema="auth"
    )
    op.create_index(
        op.f("ix_users_is_admin"), "users", ["is_admin"], unique=False, schema="auth"
    )
    op.create_index(
        op.f("ix_users_last_login"),
        "users",
        ["last_login"],
        unique=False,
        schema="auth",
    )
    op.create_index(
        op.f("ix_users_created_at"),
        "users",
        ["created_at"],
        unique=False,
        schema="auth",
    )

    # Composite indexes
    op.create_index(
        "idx_users_is_active_is_admin",
        "users",
        ["is_active", "is_admin"],
        unique=False,
        schema="auth",
    )
    op.create_index(
        "idx_users_email_is_active",
        "users",
        ["email", "is_active"],
        unique=False,
        schema="auth",
    )

    print("Users table created successfully in auth schema with TEXT password_hash!")


def downgrade() -> None:
    """Drop users table."""

    # Drop indexes first
    op.drop_index("idx_users_email_is_active", table_name="users", schema="auth")
    op.drop_index("idx_users_is_active_is_admin", table_name="users", schema="auth")
    op.drop_index(op.f("ix_users_created_at"), table_name="users", schema="auth")
    op.drop_index(op.f("ix_users_last_login"), table_name="users", schema="auth")
    op.drop_index(op.f("ix_users_is_admin"), table_name="users", schema="auth")
    op.drop_index(op.f("ix_users_is_active"), table_name="users", schema="auth")
    op.drop_index(op.f("ix_users_email"), table_name="users", schema="auth")

    # Drop table
    op.drop_table("users", schema="auth")

    print("Users table dropped!")
