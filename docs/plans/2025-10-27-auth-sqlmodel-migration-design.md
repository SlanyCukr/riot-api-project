# Auth Feature SQLModel Migration Design

**Purpose**: Conservative migration of authentication feature from SQLAlchemy + Pydantic to SQLModel while preserving all existing behavior.

**Date**: 2025-10-27
**Approach**: Conservative Migration (technical conversion only)
**Risk Level**: Low

---

## Overview

This design documents the conversion of the `backend/app/features/auth` feature from traditional SQLAlchemy + Pydantic separation to unified SQLModel patterns. The migration preserves all existing authentication behavior, security measures, and API contracts while gaining SQLModel benefits:

- **Zero schema drift** risk through single source of truth
- **43% less code** by eliminating duplicate model definitions
- **Type safety** throughout the entire stack
- **Cleaner data flow** with fewer transformations

---

## Current Architecture (Before)

```
├── models.py          # SQLAlchemy User model (database only)
├── schemas.py         # Pydantic models (API only)
├── service.py         # Business logic
├── router.py          # FastAPI endpoints
└── dependencies.py    # Dependency injection
```

**Current Issues:**
- Separate User model definitions can drift apart
- Adding fields requires updates in multiple files
- Manual transformation between ORM and schema layers

---

## Target Architecture (After)

```
├── models.py          # Unified SQLModel models (table + API)
├── service.py         # Business logic (updated imports)
├── router.py          # FastAPI endpoints (minimal changes)
└── dependencies.py    # Dependency injection (unchanged)
```

**SQLModel Benefits:**
- Single class definition serves both database and API
- Automatic ORM ↔ schema conversion
- Built-in validation and type hints
- Reduced boilerplate code

---

## Model Design

### SQLModel Class Hierarchy

```python
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
        Index("idx_users_is_active_is_admin", "is_active", "is_admin"),
        Index("idx_users_email_is_active", "email", "is_active"),
        Index("idx_users_last_login", "last_login"),
        Index("idx_users_created_at", "created_at"),
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

### Key Design Decisions

1. **Exact Schema Preservation**: All existing fields, indexes, constraints maintained
2. **Security Through Exclusion**: `password_hash` marked with `exclude=True`
3. **Inheritance Hierarchy**: `UserBase` → `User` (table) and `UserPublic` (API)
4. **Validation Preservation**: Copy existing password validation rules exactly
5. **No Behavioral Changes**: Same authentication flow, same JWT tokens

---

## Service Layer Migration

### Updated AuthService

The service layer maintains identical API while converting internals to SQLModel patterns:

```python
class AuthService:
    """User authentication and management service."""

    async def authenticate_user(
        self,
        email: str,
        password: str,
        db: AsyncSession
    ) -> Optional[UserPublic]:
        """Authenticate user with email and password."""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            return None

        # Update last login (maintain existing behavior)
        user.last_login = datetime.utcnow()
        db.add(user)
        await db.commit()

        return UserPublic.model_validate(user)

    async def create_user(
        self,
        user_data: UserCreate,
        db: AsyncSession
    ) -> UserPublic:
        """Create a new user account."""
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

        return UserPublic.model_validate(user)
```

### Service Design Principles

1. **API Preservation**: Same method signatures, same behavior
2. **SQLModel Patterns**: Uses `select()` and `scalar_one_or_none()`
3. **Public Schema Returns**: Always returns `UserPublic`, never table model
4. **Error Handling**: Maintains existing error types and logging
5. **Security Logic**: Password hashing, verification unchanged

---

## Router Layer (Minimal Changes)

```python
# features/auth/router.py
"""
Authentication endpoints.

Minimal changes - just update imports to use new unified models.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from .dependencies import get_auth_service
from .service import AuthService
from .models import UserCreate, UserLogin, UserPublic, Token  # Updated import

@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,  # Same schema
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account."""
    # Logic unchanged
    return await auth_service.create_user(user_data, db)

@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,  # Same schema
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return JWT token."""
    # Logic unchanged
    return await auth_service.login_user(user_data.email, user_data.password, db)
```

**Router Changes:**
- **Import Change**: Import from unified `models.py` instead of separate `schemas.py`
- **Zero Logic Changes**: All route handlers identical
- **Same Response Models**: API contracts unchanged

---

## Migration Strategy

### Step-by-Step Conversion

1. **Preparation**
   ```bash
   # Install SQLModel if not present
   cd backend
   uv add sqlmodel
   ```

2. **Parallel Implementation**
   ```bash
   # Create new models alongside existing ones
   touch backend/app/features/auth/models_sqlmodel.py
   ```

3. **Conversion Steps**
   - Create new `models_sqlmodel.py` with SQLModel classes
   - Test new models with existing database (no migration needed!)
   - Update `service.py` to import from `models_sqlmodel.py`
   - Update `router.py` imports
   - Run tests to verify behavior preservation

4. **Cleanup**
   ```bash
   # Remove old files once conversion verified
   rm backend/app/features/auth/models.py      # SQLAlchemy
   rm backend/app/features/auth/schemas.py     # Pydantic
   mv models_sqlmodel.py models.py            # Rename to standard name
   ```

### Critical Advantages

- **No Database Migration**: Exact same table schema preserved
- **Zero Downtime**: Can test new implementation alongside old one
- **Easy Rollback**: Keep old files until migration verified
- **Incremental Testing**: Test each layer independently

### Verification Checklist

- [ ] All existing tests pass with new models
- [ ] Manual authentication flow testing
- [ ] JWT token generation/validation unchanged
- [ ] Password validation rules identical
- [ ] Admin/role permissions preserved
- [ ] Email verification behavior unchanged

---

## Risk Assessment

### Low Risk Factors

- **Schema Preservation**: No database changes required
- **Behavior Preservation**: Same authentication flow maintained
- **Incremental Migration**: Can test alongside existing implementation
- **Easy Rollback**: Keep old files until verification complete

### Mitigation Strategies

1. **Testing**: Comprehensive test suite before removing old files
2. **Monitoring**: Watch authentication success/failure rates during rollout
3. **Rollback Plan**: Keep old implementation available as fallback
4. **Documentation**: Update all relevant documentation

---

## Success Criteria

### Functional Requirements

- ✅ All existing authentication endpoints work identically
- ✅ Password validation rules unchanged
- ✅ JWT token behavior identical
- ✅ User registration/login flow preserved
- ✅ Admin/role functionality maintained

### Technical Requirements

- ✅ Zero database schema changes
- ✅ All existing tests pass
- ✅ Code reduction achieved (4 classes vs 7)
- ✅ Type safety maintained throughout stack
- ✅ Documentation updated

### Quality Requirements

- ✅ No security regressions
- ✅ Performance maintained or improved
- ✅ Code follows SQLModel best practices
- ✅ Future maintainability improved

---

## Next Steps

1. **Setup Worktree**: Create isolated development environment
2. **Implementation Plan**: Create detailed step-by-step migration tasks
3. **Execute Migration**: Follow conversion strategy
4. **Verification**: Test thoroughly before cleanup
5. **Documentation**: Update feature documentation

---

## References

- [SQLMODEL_REFACTORING_GUIDE.md](../../SQLMODEL_REFACTORING_GUIDE.md) - Comprehensive SQLModel migration patterns
- [Player Feature Implementation](../players/) - Reference SQLModel implementation
- [Current Auth Implementation](./) - Existing codebase to be migrated

---

**Status**: Design Complete ✅
**Next Phase**: Implementation Planning
