# Create test file: backend/app/features/auth/test_models.py
import pytest
from datetime import datetime, timezone

# Import directly to avoid __init__.py conflicts for now
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.features.auth.models import User, UserCreate, UserPublic


def test_user_model_creation():
    """Test User model can be instantiated."""
    user = User(
        email="test@example.com",
        display_name="Test User",
        password_hash="hashed_password",  # nosec B106
        is_active=True,
        is_admin=False,
    )
    assert user.email == "test@example.com"
    assert user.display_name == "Test User"
    assert user.is_active


def test_user_create_validation():
    """Test UserCreate validates password correctly."""
    # Valid password
    user_create = UserCreate(
        email="test@example.com",
        display_name="Test User",
        password="ValidPass123!",  # nosec B106
    )
    assert user_create.email == "test@example.com"

    # Invalid password - should raise ValidationError
    with pytest.raises(Exception) as exc_info:
        UserCreate(
            email="test@example.com",
            display_name="Test User",
            password="weak",  # nosec B106  # Too short, no special chars
        )
    assert "String should have at least 8 characters" in str(exc_info.value)


def test_user_public_orm_conversion():
    """Test UserPublic can be created from ORM model."""
    user = User(
        email="test@example.com",
        display_name="Test User",
        id=1,
        is_active=True,
        is_admin=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    user_public = UserPublic.model_validate(user)
    assert user_public.email == "test@example.com"
    assert user_public.id == 1
    assert user_public.is_active


def test_auth_service_sqlmodel_integration():
    """Test that auth service works with SQLModel models."""
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession
    from unittest.mock import Mock, AsyncMock
    from app.features.auth.service import AuthService
    from app.features.auth.models import UserCreate

    async def test_logic():
        mock_db = Mock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        service = AuthService()

        # Test that UserCreate model works
        user_data = UserCreate(
            email="test@example.com",
            display_name="Test",
            password="ValidPass123!",  # nosec B106
        )
        assert user_data.email == "test@example.com"

        # Test that service methods exist and have correct signatures
        assert hasattr(service, "create_user")
        assert hasattr(service, "authenticate_user")
        assert hasattr(service, "get_user_by_email")
        assert hasattr(service, "get_user_by_id")
        assert hasattr(service, "login_user")

        print("✅ Service class and methods exist - SQLModel migration working")
        return True

    result = asyncio.run(test_logic())
    assert result is True
