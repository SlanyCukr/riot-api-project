#!/usr/bin/env python3
"""
Script to create admin user accounts for the Riot API application.

This script should be run in production/development environments to create
admin accounts without hardcoding passwords in migrations.

Usage:
    # Interactive mode (prompts for input):
    docker compose exec backend uv run python scripts/create_admin_user.py

    # Environment variables mode:
    ADMIN_EMAIL="admin@example.com" \
    ADMIN_DISPLAY_NAME="Admin User" \
    ADMIN_PASSWORD="SecurePassword123!" \
    docker compose exec backend uv run python scripts/create_admin_user.py

Environment Variables:
    ADMIN_EMAIL: Admin user email address
    ADMIN_DISPLAY_NAME: Display name for admin user
    ADMIN_PASSWORD: Secure password for admin user
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from getpass import getpass

import asyncpg
from passlib.context import CryptContext


# Password hashing context using Argon2id
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def get_database_url() -> str:
    """Get database URL from environment or use default."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        # Construct from individual components
        postgres_password = os.getenv("POSTGRES_PASSWORD", "dev_password")
        postgres_user = os.getenv("POSTGRES_USER", "riot_api_user")
        postgres_db = os.getenv("POSTGRES_DB", "riot_api_db")
        postgres_host = os.getenv("POSTGRES_HOST", "postgres")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")

        db_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"

    # Convert asyncpg URL if needed
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    return db_url


def validate_email(email: str) -> bool:
    """Basic email validation."""
    return "@" in email and "." in email.split("@")[1]


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password meets security requirements.

    Requirements:
    - At least 8 characters
    - At least one lowercase letter
    - At least one uppercase letter
    - At least one digit
    - At least one special character

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    special_chars = '!@#$%^&*(),.?":{}|<>'
    if not any(c in special_chars for c in password):
        return (
            False,
            f"Password must contain at least one special character ({special_chars})",
        )

    return True, ""


def get_user_input() -> tuple[str, str, str]:
    """Get user input interactively or from environment variables."""
    print("=== Create Admin User ===\n")

    # Try to get from environment first
    email = os.getenv("ADMIN_EMAIL")
    display_name = os.getenv("ADMIN_DISPLAY_NAME")
    password = os.getenv("ADMIN_PASSWORD")

    # If not in environment, prompt user
    if not email:
        email = input("Admin Email: ").strip()
        if not validate_email(email):
            print("Error: Invalid email address")
            sys.exit(1)

    if not display_name:
        display_name = input("Display Name: ").strip()
        if not display_name:
            print("Error: Display name cannot be empty")
            sys.exit(1)

    if not password:
        password = getpass("Password: ")
        password_confirm = getpass("Confirm Password: ")

        if password != password_confirm:
            print("Error: Passwords do not match")
            sys.exit(1)

    # Validate password
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        print(f"Error: {error_msg}")
        sys.exit(1)

    return email, display_name, password


async def create_admin_user(email: str, display_name: str, password: str) -> None:
    """Create an admin user in the database."""
    db_url = get_database_url()

    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)

        try:
            # Check if user already exists
            existing_user = await conn.fetchrow(
                "SELECT id FROM auth.users WHERE email = $1", email
            )

            if existing_user:
                print(f"\nError: User with email '{email}' already exists")
                sys.exit(1)

            # Hash password
            print("\nHashing password...")
            password_hash = pwd_context.hash(password)

            # Insert admin user
            print("Creating admin user...")
            now = datetime.now(timezone.utc)

            await conn.execute(
                """
                INSERT INTO auth.users (
                    email, password_hash, display_name,
                    is_active, is_admin, email_verified, email_verified_at,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, true, true, true, $4, $4, $4)
                """,
                email,
                password_hash,
                display_name,
                now,
            )

            print("\n✅ Admin user created successfully!")
            print(f"   Email: {email}")
            print(f"   Display Name: {display_name}")
            print("   Admin: Yes")
            print("\nYou can now log in with these credentials.")

        finally:
            await conn.close()

    except asyncpg.PostgresError as e:
        print(f"\nDatabase error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


async def main() -> None:
    """Main entry point."""
    try:
        email, display_name, password = get_user_input()
        await create_admin_user(email, display_name, password)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
