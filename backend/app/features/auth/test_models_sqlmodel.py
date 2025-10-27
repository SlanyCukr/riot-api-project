# Create test file: backend/app/features/auth/test_models_sqlmodel.py
import pytest
from datetime import datetime

# Import directly from the module to avoid package-level imports that conflict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.features.auth.models_sqlmodel import User, UserCreate, UserPublic


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
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    user_public = UserPublic.model_validate(user)
    assert user_public.email == "test@example.com"
    assert user_public.id == 1
    assert user_public.is_active
