#!/usr/bin/env python3
"""Reset admin user password.

Usage:
    docker compose exec backend python reset_admin_password.py
"""

import asyncio
import sys
from getpass import getpass

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.features.auth.models import User
from app.features.auth.service import AuthService


async def reset_admin_password():
    """Reset admin user password interactively."""
    print("Admin Password Reset")
    print("=" * 50)

    # Get admin email
    admin_email = input("Enter admin email: ").strip()
    if not admin_email:
        print("Error: Email cannot be empty")
        sys.exit(1)

    # Get new password
    new_password = getpass("Enter new password: ")
    confirm_password = getpass("Confirm new password: ")

    if new_password != confirm_password:
        print("Error: Passwords do not match")
        sys.exit(1)

    if len(new_password) < 8:
        print("Error: Password must be at least 8 characters")
        sys.exit(1)

    # Update password in database
    async with AsyncSessionLocal() as db:
        # Find user
        result = await db.execute(select(User).where(User.email == admin_email))
        user = result.scalar_one_or_none()

        if not user:
            print(f"Error: User with email '{admin_email}' not found")
            sys.exit(1)

        # Hash new password
        new_password_hash = AuthService.get_password_hash(new_password)

        # Update user
        user.password_hash = new_password_hash

        # Make sure user is admin
        if not user.is_admin:
            print(
                f"Warning: User '{admin_email}' is not an admin. Setting is_admin=True"
            )
            user.is_admin = True

        await db.commit()

        print()
        print("✓ Password reset successful!")
        print(f"  Email: {user.email}")
        print(f"  Admin: {user.is_admin}")
        print(f"  Display Name: {user.display_name}")


if __name__ == "__main__":
    asyncio.run(reset_admin_password())
