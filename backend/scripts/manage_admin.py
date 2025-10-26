#!/usr/bin/env python3
"""
Admin user management script for the Riot API application.

This script provides commands to create and reset admin user accounts.

Usage:
    # Create a new admin user
    docker compose exec backend uv run python scripts/manage_admin.py create

    # Reset an existing admin user's password
    docker compose exec backend uv run python scripts/manage_admin.py reset
"""

import asyncio
import sys
from getpass import getpass

from sqlalchemy import select

from app.core.database import db_manager
from app.features.auth.models import User
from app.features.auth.service import AuthService


def validate_email(email: str) -> bool:
    """
    Basic email validation.

    :param email: Email address to validate
    :returns: True if valid, False otherwise
    """
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

    :param password: Password to validate
    :returns: Tuple of (is_valid, error_message)
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


def get_password_input() -> str:
    """
    Get and validate password input from user.

    :returns: Validated password
    :raises SystemExit: If passwords don't match or validation fails
    """
    password = getpass("Password: ")
    password_confirm = getpass("Confirm Password: ")

    if password != password_confirm:
        print("Error: Passwords do not match")
        sys.exit(1)

    is_valid, error_msg = validate_password(password)
    if not is_valid:
        print(f"Error: {error_msg}")
        sys.exit(1)

    return password


async def create_admin_user() -> None:
    """
    Create a new admin user interactively.

    :raises SystemExit: On validation errors or if user already exists
    """
    print("=== Create Admin User ===\n")

    # Get email
    email = input("Admin Email: ").strip()
    if not email:
        print("Error: Email cannot be empty")
        sys.exit(1)

    if not validate_email(email):
        print("Error: Invalid email address")
        sys.exit(1)

    # Get display name
    display_name = input("Display Name: ").strip()
    if not display_name:
        print("Error: Display name cannot be empty")
        sys.exit(1)

    # Get and validate password
    password = get_password_input()

    # Create user in database
    async with db_manager.get_session() as db:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"\nError: User with email '{email}' already exists")
            sys.exit(1)

        # Create new admin user
        password_hash = AuthService.get_password_hash(password)

        new_user = User(
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            is_active=True,
            is_admin=True,
            email_verified=True,
        )

        db.add(new_user)
        await db.commit()

        print("\n✅ Admin user created successfully!")
        print(f"   Email: {email}")
        print(f"   Display Name: {display_name}")
        print("   Admin: Yes")
        print("\nYou can now log in with these credentials.")


async def reset_admin_password() -> None:
    """
    Reset an existing admin user's password interactively.

    :raises SystemExit: On validation errors or if user not found
    """
    print("=== Reset Admin Password ===\n")

    # Get admin email
    email = input("Enter admin email: ").strip()
    if not email:
        print("Error: Email cannot be empty")
        sys.exit(1)

    # Get and validate new password
    print("\nEnter new password:")
    password = get_password_input()

    # Update password in database
    async with db_manager.get_session() as db:
        # Find user
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            print(f"\nError: User with email '{email}' not found")
            sys.exit(1)

        # Hash new password
        new_password_hash = AuthService.get_password_hash(password)

        # Update user
        user.password_hash = new_password_hash

        # Make sure user is admin
        if not user.is_admin:
            print(f"\nWarning: User '{email}' is not an admin. Setting is_admin=True")
            user.is_admin = True

        await db.commit()

        print("\n✅ Password reset successful!")
        print(f"   Email: {user.email}")
        print(f"   Display Name: {user.display_name}")
        print(f"   Admin: {user.is_admin}")


def print_usage() -> None:
    """Print usage information."""
    print("Usage:")
    print("  python scripts/manage_admin.py create   - Create a new admin user")
    print("  python scripts/manage_admin.py reset    - Reset an admin user's password")


async def main() -> None:
    """
    Main entry point.

    :raises SystemExit: If invalid command provided
    """
    if len(sys.argv) < 2:
        print("Error: Missing command\n")
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    try:
        if command == "create":
            await create_admin_user()
        elif command == "reset":
            await reset_admin_password()
        else:
            print(f"Error: Unknown command '{command}'\n")
            print_usage()
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
