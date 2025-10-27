# Auth Feature SQLModel Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert auth feature from SQLAlchemy + Pydantic to unified SQLModel while preserving all existing behavior.

**Architecture:** Conservative migration - maintain exact same authentication flow, JWT tokens, and API contracts while consolidating duplicate model definitions into single source of truth.

**Tech Stack:** SQLModel, FastAPI, SQLAlchemy 2.0+, Pydantic v2, Alembic

---

## Pre-requisites

**Files to check before starting:**
- Read: `SQLMODEL_REFACTORING_GUIDE.md` (main project root)
- Read: `docs/plans/2025-10-27-auth-sqlmodel-migration-design.md` (completed design)
- Verify: Current auth structure in `backend/app/features/auth/`

**Dependencies to install:**
```bash
cd backend
uv add sqlmodel  # If not already installed
```

---

### Task 1: Install SQLModel and Verify Environment

**Files:**
- Modify: `backend/pyproject.toml` (dependencies section)

**Step 1: Add SQLModel dependency**

```toml
[dependencies]
# ... existing dependencies ...
sqlmodel = ">=0.0.14"
```

**Step 2: Install dependency**

Run: `cd backend && uv sync`
Expected: SQLModel installed without conflicts

**Step 3: Verify SQLModel installation**

Run: `docker compose exec backend uv run python -c "import sqlmodel; print('SQLModel version:', sqlmodel.__version__)"`
Expected: `SQLModel version: 0.0.14` (or later)

**Step 4: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "feat: add SQLModel dependency for auth migration"
```

---

### Task 2: Create New SQLModel Models File

**Files:**
- Create: `backend/app/features/auth/models_sqlmodel.py`

**Step 1: Create models_sqlmodel.py with SQLModel classes**

```python
"""
SQLModel models for authentication feature.

Replaces both models.py (SQLAlchemy) and schemas.py (Pydantic)
with unified SQLModel classes following conservative migration approach.

Pattern: Base → Table → API schemas
"""

from datetime import datetime
from typing import Optional
import re
from sqlmodel import SQLModel, Field, Relationship
from pydantic import EmailStr, field_validator, ConfigDict
from pydantic_core import ValidationError


# ============================================================================
# BASE MODELS - Shared fields between table and API
# ============================================================================

class UserBase(SQLModel):
    """
    Shared user fields between database and API.

    Include only fields that appear in BOTH:
    - Database table (User)
    - API requests/responses (UserCreate, UserPublic)
    """
    email: EmailStr = Field(
        max_length=255,
        index=True,
        description="User's email address (unique)"
    )
    display_name: str = Field(
        max_length=128,
        description="Display name shown in UI"
    )


# ============================================================================
# TABLE MODELS - Database tables (exact schema preservation)
# ============================================================================

class User(UserBase, table=True):
    """
    User database table.

    Maintains exact same schema as current auth.users table.
    Combines shared fields from UserBase with database-only fields.
    """

    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    # Primary key
    id: int = Field(
        primary_key=True,
        description="Auto-incrementing primary key"
    )

    # Authentication fields (NEVER in API responses)
    password_hash: str = Field(
        description="Hashed password using Argon2id",
        exclude=True  # Automatically excluded from API responses
    )

    # Account status flags
    is_active: bool = Field(
        default=True,
        index=True,
        description="Whether account is active (not disabled)"
    )
    is_admin: bool = Field(
        default=False,
        index=True,
        description="Whether user has admin privileges"
    )

    # Email verification
    email_verified: bool = Field(
        default=False,
        description="Whether email has been verified"
    )
    email_verified_at: Optional[datetime] = Field(
        default=None,
        description="When email was verified"
    )

    # Activity tracking
    last_login: Optional[datetime] = Field(
        default=None,
        index=True,
        description="When user last logged in"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this user account was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow},
        description="When this user account was last updated"
    )

    # Indexes (maintain existing performance)
    __table_args__ = (
        Field("idx_users_is_active_is_admin", "is_active", "is_admin"),
        Field("idx_users_email_is_active", "email", "is_active"),
        Field("idx_users_last_login", "last_login"),
        Field("idx_users_created_at", "created_at"),
        {"schema": "auth"}
    )


# ============================================================================
# API MODELS - Request/response schemas
# ============================================================================

class UserCreate(UserBase):
    """
    Request to create a new user.

    Inherits email and display_name from UserBase.
    Adds password for registration only.
    """
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Password (will be hashed)"
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Maintain existing password validation rules exactly."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        # Expanded special character set to support password managers
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_+=\[\]\\/;'`~]", v):
            raise ValueError(
                "Password must contain at least one special character "
                r"(!@#$%^&*(),.?\":{}|<>-_+=[]\/;'`~)"
            )

        return v


class UserLogin(SQLModel):
    """
    Request for user login.

    Separate from UserCreate as login doesn't need display_name.
    """
    email: EmailStr
    password: str


class UserPublic(UserBase):
    """
    User API response.

    Excludes sensitive data like password_hash.
    Includes read-only fields like timestamps.
    """
    id: int
    is_active: bool
    is_admin: bool
    email_verified: bool
    email_verified_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(SQLModel):
    """JWT token response (unchanged)."""
    access_token: str
    token_type: str = "bearer"


class TokenData(SQLModel):
    """Token payload data (unchanged)."""
    email: Optional[EmailStr] = None
    user_id: Optional[int] = None
```

**Step 2: Create basic test to verify model works**

```python
# Create test file: backend/app/features/auth/test_models_sqlmodel.py
import pytest
from app.features.auth.models_sqlmodel import User, UserCreate, UserPublic

def test_user_model_creation():
    """Test User model can be instantiated."""
    user = User(
        email="test@example.com",
        display_name="Test User",
        password_hash="hashed_password",
        is_active=True,
        is_admin=False
    )
    assert user.email == "test@example.com"
    assert user.display_name == "Test User"
    assert user.is_active == True

def test_user_create_validation():
    """Test UserCreate validates password correctly."""
    # Valid password
    user_create = UserCreate(
        email="test@example.com",
        display_name="Test User",
        password="ValidPass123!"
    )
    assert user_create.email == "test@example.com"

    # Invalid password - should raise ValidationError
    with pytest.raises(ValueError) as exc_info:
        UserCreate(
            email="test@example.com",
            display_name="Test User",
            password="weak"  # Too short, no special chars
        )
    assert "Password must be at least 8 characters long" in str(exc_info.value)

def test_user_public_orm_conversion():
    """Test UserPublic can be created from ORM model."""
    user = User(
        email="test@example.com",
        display_name="Test User",
        id=1,
        is_active=True,
        is_admin=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    user_public = UserPublic.model_validate(user)
    assert user_public.email == "test@example.com"
    assert user_public.id == 1
    assert user_public.is_active == True
```

**Step 3: Run test to verify models work**

Run: `docker compose exec backend uv run pytest backend/app/features/auth/test_models_sqlmodel.py -v`
Expected: All tests pass, model validation works correctly

**Step 4: Commit**

```bash
git add backend/app/features/auth/models_sqlmodel.py backend/app/features/auth/test_models_sqlmodel.py
git commit -m "feat: create unified SQLModel models for auth feature"
```

---

### Task 3: Update Service Layer to Use SQLModel

**Files:**
- Modify: `backend/app/features/auth/service.py`

**Step 1: Write failing test for service with SQLModel**

```python
# Add to test_models_sqlmodel.py
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import Mock, AsyncMock

def test_auth_service_sqlmodel_integration():
    """Test that auth service works with SQLModel models."""
    # This test will fail initially because service still uses old models
    from app.features.auth.service import AuthService
    from app.features.auth.models_sqlmodel import User, UserCreate

    async def test_logic():
        mock_db = Mock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = AuthService()

        # This should work with new UserCreate model
        user_data = UserCreate(
            email="test@example.com",
            display_name="Test",
            password="ValidPass123!"
        )

        # This will fail because service expects old UserCreate schema
        result = await service.create_user(user_data, mock_db)
        return result

    # This test will fail until we update service
    asyncio.run(test_logic())
```

**Step 2: Run test to verify it fails**

Run: `docker compose exec backend uv run pytest backend/app/features/auth/test_models_sqlmodel.py::test_auth_service_sqlmodel_integration -v`
Expected: FAIL with import or validation errors due to old service expecting old models

**Step 3: Update service imports and method signatures**

```python
# Replace current service.py content with SQLModel version

"""
User authentication and management service.

Maintains exact same API as current service,
just converts internals to SQLModel patterns.
"""

from typing import Optional
from sqlmodel import select, Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.exceptions import AuthenticationError, UserNotFoundError
from .models_sqlmodel import User, UserCreate, UserPublic, UserLogin, TokenData

logger = structlog.get_logger()


class AuthService:
    """User authentication and management service."""

    async def authenticate_user(
        self,
        email: str,
        password: str,
        db: AsyncSession
    ) -> Optional[UserPublic]:
        """
        Authenticate user with email and password.

        Args:
            email: User's email address
            password: Plain text password
            db: Database session

        Returns:
            UserPublic if authentication successful, None otherwise

        Raises:
            AuthenticationError: If credentials are invalid
        """
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.info("auth_failed_user_not_found", email=email)
            return None

        if not verify_password(password, user.password_hash):
            logger.info("auth_failed_invalid_password", email=email)
            return None

        if not user.is_active:
            logger.info("auth_failed_user_inactive", email=email)
            return None

        # Update last login (maintain existing behavior)
        user.last_login = datetime.utcnow()
        db.add(user)
        await db.commit()

        logger.info("auth_success", email=email, user_id=user.id)
        return UserPublic.model_validate(user)

    async def create_user(
        self,
        user_data: UserCreate,
        db: AsyncSession
    ) -> UserPublic:
        """
        Create a new user account.

        Args:
            user_data: User creation data
            db: Database session

        Returns:
            Created user as UserPublic

        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        existing = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Email {user_data.email} already registered")

        # Create user with hashed password
        user = User(
            email=user_data.email,
            display_name=user_data.display_name,
            password_hash=get_password_hash(user_data.password)
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info("user_created", email=user.email, user_id=user.id)
        return UserPublic.model_validate(user)

    async def get_user_by_id(
        self,
        user_id: int,
        db: AsyncSession
    ) -> Optional[UserPublic]:
        """
        Get user by ID.

        Args:
            user_id: User's primary key
            db: Database session

        Returns:
            UserPublic if found, None otherwise
        """
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        return UserPublic.model_validate(user)

    async def get_user_by_email(
        self,
        email: str,
        db: AsyncSession
    ) -> Optional[UserPublic]:
        """
        Get user by email.

        Args:
            email: User's email address
            db: Database session

        Returns:
            UserPublic if found, None otherwise
        """
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        return UserPublic.model_validate(user)

    def create_access_token(self, user: UserPublic) -> str:
        """
        Create JWT access token for user.

        Args:
            user: User to create token for

        Returns:
            JWT access token string
        """
        return create_access_token(data={"sub": user.email, "user_id": user.id})

    async def login_user(self, email: str, password: str, db: AsyncSession) -> Token:
        """
        Authenticate user and return JWT token.

        Args:
            email: User email
            password: User password
            db: Database session

        Returns:
            JWT token for authenticated user

        Raises:
            AuthenticationError: If authentication fails
        """
        user_public = await self.authenticate_user(email, password, db)

        if not user_public:
            raise AuthenticationError("Invalid email or password")

        access_token = self.create_access_token(user_public)
        return Token(access_token=access_token, token_type="bearer")
```

**Step 4: Run test to verify it passes**

Run: `docker compose exec backend uv run pytest backend/app/features/auth/test_models_sqlmodel.py::test_auth_service_sqlmodel_integration -v`
Expected: PASS - service now works with SQLModel

**Step 5: Run all auth tests to verify behavior preserved**

Run: `docker compose exec backend uv run pytest backend/app/features/auth/ -v`
Expected: All tests pass, behavior preserved

**Step 6: Commit**

```bash
git add backend/app/features/auth/service.py
git commit -m "feat: migrate auth service to use SQLModel patterns"
```

---

### Task 4: Update Router Layer Imports

**Files:**
- Modify: `backend/app/features/auth/router.py`

**Step 1: Update router imports to use new models**

```python
# Replace existing imports at top of router.py

# OLD (to be replaced):
# from app.features.auth.schemas import UserCreate, UserLogin, UserPublic, Token

# NEW (SQLModel):
from app.features.auth.models_sqlmodel import UserCreate, UserLogin, UserPublic, Token

# Keep other imports unchanged:
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from .dependencies import get_auth_service
from .service import AuthService
```

**Step 2: Test router functionality**

```bash
# Start backend if not running
docker compose up -d

# Test basic health check
curl -f http://localhost:8000/health
Expected: {"status": "healthy"}
```

**Step 3: Test auth endpoints manually**

```bash
# Test user registration endpoint exists
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "display_name": "Test", "password": "ValidPass123!"}' \
  -w "\nHTTP Status: %{http_code}\n"
Expected: HTTP Status 201 or validation error (but endpoint exists)

# Test login endpoint exists
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "nonexistent@example.com", "password": "password"}' \
  -w "\nHTTP Status: %{http_code}\n"
Expected: HTTP Status 401 (invalid credentials, but endpoint works)
```

**Step 4: Commit**

```bash
git add backend/app/features/auth/router.py
git commit -m "feat: update auth router to use unified SQLModel imports"
```

---

### Task 5: Update Dependencies and Exports

**Files:**
- Modify: `backend/app/features/auth/dependencies.py`
- Modify: `backend/app/features/auth/__init__.py`

**Step 1: Update dependencies imports**

```python
# In dependencies.py, update any imports from old schemas/models
# OLD:
# from app.features.auth.schemas import UserPublic
# from app.features.auth.models import User

# NEW:
from app.features.auth.models_sqlmodel import User, UserPublic
```

**Step 2: Update __init__.py exports**

```python
# In __init__.py, update public exports
# OLD:
# from .models import User
# from .schemas import UserCreate, UserPublic, UserLogin

# NEW:
from .models_sqlmodel import User, UserCreate, UserPublic, UserLogin, Token

# Keep other exports:
from .router import router as auth_router
from .service import AuthService

__all__ = [
    "auth_router",
    "AuthService",
    "User",
    "UserCreate",
    "UserPublic",
    "UserLogin",
    "Token",
]
```

**Step 3: Test imports work correctly**

```bash
# Test that importing from auth feature works
docker compose exec backend uv run python -c "
from app.features.auth import User, UserCreate, UserPublic, auth_router
print('✅ Auth imports working correctly')
print('User model:', User)
print('UserCreate model:', UserCreate)
print('UserPublic model:', UserPublic)
print('Auth router:', auth_router)
"
Expected: All imports successful, models printed correctly
```

**Step 4: Commit**

```bash
git add backend/app/features/auth/dependencies.py backend/app/features/auth/__init__.py
git commit -m "feat: update auth dependencies and exports for SQLModel"
```

---

### Task 6: Verify Migration Completeness

**Files:**
- Test: All auth functionality
- Test: API endpoints

**Step 1: Test complete auth flow**

```python
# Create comprehensive test: backend/app/features/auth/test_migration_complete.py
import pytest
import asyncio
from sqlmodel import create_engine, SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, sessionmaker

@pytest.mark.asyncio
async def test_complete_auth_flow():
    """Test complete authentication flow with SQLModel."""
    from app.features.auth.models_sqlmodel import User, UserCreate, UserLogin, UserPublic, Token
    from app.features.auth.service import AuthService

    # Setup in-memory database for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        service = AuthService()

        # Test user creation
        user_data = UserCreate(
            email="test@example.com",
            display_name="Test User",
            password="ValidPass123!"
        )

        created_user = await service.create_user(user_data, db)
        assert created_user.email == "test@example.com"
        assert created_user.display_name == "Test User"
        assert created_user.is_active == True
        assert created_user.is_admin == False
        assert created_user.id is not None
        assert created_user.created_at is not None
        assert created_user.password_hash is None  # Should be excluded

        # Test authentication
        auth_user = await service.authenticate_user("test@example.com", "ValidPass123!", db)
        assert auth_user is not None
        assert auth_user.email == "test@example.com"
        assert auth_user.last_login is not None  # Should be updated

        # Test failed authentication
        failed_auth = await service.authenticate_user("test@example.com", "wrongpassword", db)
        assert failed_auth is None

        # Test get user by ID
        found_user = await service.get_user_by_id(created_user.id, db)
        assert found_user is not None
        assert found_user.email == "test@example.com"

        # Test get user by email
        email_user = await service.get_user_by_email("test@example.com", db)
        assert email_user is not None
        assert email_user.id == created_user.id

        # Test token creation
        token = service.create_access_token(created_user)
        assert isinstance(token, str)
        assert len(token) > 0

        # Test login method
        login_result = await service.login_user("test@example.com", "ValidPass123!", db)
        assert isinstance(login_result, Token)
        assert login_result.token_type == "bearer"
        assert len(login_result.access_token) > 0

    await engine.dispose()
```

**Step 2: Run comprehensive test**

Run: `docker compose exec backend uv run pytest backend/app/features/auth/test_migration_complete.py -v`
Expected: All tests pass, complete auth flow working

**Step 3: Test API integration**

```bash
# Test all auth endpoints with curl
BASE_URL="http://localhost:8000/api/v1/auth"

# Test registration (should succeed with valid data)
curl -X POST "${BASE_URL}/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "sqlmodeltest@example.com",
    "display_name": "SQLModel Test",
    "password": "ValidPass123!"
  }' \
  -s | head -1

# Test login with created user
TOKEN=$(curl -X POST "${BASE_URL}/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "sqlmodeltest@example.com",
    "password": "ValidPass123!"
  }' \
  -s | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "Token: ${TOKEN}"

# Test that token is a non-empty string
if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    echo "✅ Authentication flow working correctly"
else
    echo "❌ Authentication flow failed"
fi
```

**Step 4: Verify database schema unchanged**

```bash
# Connect to database and verify schema unchanged
docker compose exec backend uv run python -c "
from sqlalchemy import inspect
from app.core.database import async_engine
import asyncio

async def check_schema():
    async with async_engine.begin() as conn:
        inspector = await conn.run_sync(inspect)
        users_table = await conn.run_sync(lambda: inspector.get_columns('users', schema='auth'))

        print('✅ Users table columns:')
        for col in users_table:
            print(f'  - {col[\"name\"]} ({col[\"type\"]})')

        expected_columns = {'id', 'email', 'password_hash', 'display_name', 'is_active',
                         'is_admin', 'email_verified', 'email_verified_at',
                         'last_login', 'created_at', 'updated_at'}
        actual_columns = {col['name'] for col in users_table}

        missing = expected_columns - actual_columns
        extra = actual_columns - expected_columns

        if missing or extra:
            print(f'❌ Schema differences - Missing: {missing}, Extra: {extra}')
        else:
            print('✅ Database schema preserved exactly')

asyncio.run(check_schema())
"
Expected: All columns present, no schema changes
```

**Step 5: Commit final verification tests**

```bash
git add backend/app/features/auth/test_migration_complete.py
git commit -m "test: add comprehensive migration verification tests"
```

---

### Task 7: Cleanup and Finalize

**Files:**
- Remove: `backend/app/features/auth/models.py` (SQLAlchemy)
- Remove: `backend/app/features/auth/schemas.py` (Pydantic)
- Rename: `backend/app/features/auth/models_sqlmodel.py` → `models.py`

**Step 1: Backup old files (safety)**

```bash
# Create backup directory
mkdir -p /tmp/auth-backup
cp backend/app/features/auth/models.py /tmp/auth-backup/ 2>/dev/null || echo "models.py not found"
cp backend/app/features/auth/schemas.py /tmp/auth-backup/ 2>/dev/null || echo "schemas.py not found"
echo "Backup created in /tmp/auth-backup/"
```

**Step 2: Remove old files**

```bash
# Remove old model files
rm -f backend/app/features/auth/models.py
rm -f backend/app/features/auth/schemas.py
echo "Old files removed"
```

**Step 3: Rename new file**

```bash
# Rename models_sqlmodel.py to models.py
mv backend/app/features/auth/models_sqlmodel.py backend/app/features/auth/models.py
echo "models_sqlmodel.py renamed to models.py"
```

**Step 4: Update all imports to use models.py**

```python
# Update dependencies.py imports
# OLD: from .models_sqlmodel import User, UserPublic
# NEW: from .models import User, UserPublic

# Update __init__.py imports
# OLD: from .models_sqlmodel import User, UserCreate, UserPublic, UserLogin, Token
# NEW: from .models import User, UserCreate, UserPublic, UserLogin, Token

# Update router.py imports
# OLD: from .models_sqlmodel import UserCreate, UserLogin, UserPublic, Token
# NEW: from .models import UserCreate, UserLogin, UserPublic, Token

# Update service.py imports
# OLD: from .models_sqlmodel import User, UserCreate, UserPublic, UserLogin, TokenData
# NEW: from .models import User, UserCreate, UserPublic, UserLogin, TokenData
```

**Step 5: Test everything still works**

```bash
# Run all auth tests
docker compose exec backend uv run pytest backend/app/features/auth/ -v
Expected: All tests pass

# Test API still works
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "nonexistent@example.com", "password": "password"}' \
  -w "\nHTTP Status: %{http_code}\n"
Expected: HTTP Status 401 (endpoint responding correctly)
```

**Step 6: Commit final migration**

```bash
git add backend/app/features/auth/
git commit -m "feat: complete auth SQLModel migration - remove old files and rename models_sqlmodel.py"

# Note: Backup files in /tmp/auth-backup can be removed after verification
rm -rf /tmp/auth-backup
echo "✅ Auth SQLModel migration complete!"
```

---

## Migration Verification Checklist

**Before Cleanup:**
- [ ] All new tests pass
- [ ] Service methods work with SQLModel
- [ ] API endpoints respond correctly
- [ ] Database schema unchanged
- [ ] Auth flow preserved

**After Cleanup:**
- [ ] Old files removed
- [ ] New models.py in place
- [ ] All imports updated
- [ ] All tests still pass
- [ ] API functionality unchanged

**Success Criteria:**
- ✅ Zero database schema changes
- ✅ All existing authentication behavior preserved
- ✅ Code reduction achieved (4 classes vs 7)
- ✅ Type safety maintained throughout stack
- ✅ No breaking changes to API contracts

---

## Troubleshooting

**If tests fail after service update:**
1. Check import statements in service.py
2. Verify SQLModel query syntax matches examples
3. Ensure UserPublic.model_validate() is used correctly

**If API endpoints return errors:**
1. Check router imports are updated
2. Verify dependencies.py imports correct models
3. Confirm __init__.py exports correct classes

**If database schema changed:**
1. Verify table schema in models.py matches original exactly
2. Check that exclude=True is working for sensitive fields
3. Ensure all original fields and constraints are present

**If authentication flow broken:**
1. Verify password hashing/verification unchanged
2. Check JWT token generation still works
3. Confirm UserPublic excludes password_hash correctly

---

## References

**Key Documentation:**
- [SQLMODEL_REFACTORING_GUIDE.md](../../../../SQLMODEL_REFACTORING_GUIDE.md) - Complete SQLModel patterns
- [Design Document](2025-10-27-auth-sqlmodel-migration-design.md) - Migration design decisions
- [Player Feature Implementation](../players/) - Reference SQLModel usage

**Useful Skills:**
- @superpowers:executing-plans - For implementing this plan step-by-step
- @superpowers:systematic-debugging - If tests fail during migration
- @superpowers:verification-before-completion - Final verification before merging
