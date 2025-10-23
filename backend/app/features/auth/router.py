"""Authentication router with login, logout, and user management endpoints."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from .dependencies import get_current_active_user, get_current_admin_user
from .models import User
from .schemas import Token, UserCreate, UserResponse
from .service import AuthService, get_auth_service

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
) -> Token:
    """Login endpoint using OAuth2 password flow.

    Authenticates user with email and password, returns JWT access token.
    Updates last_login timestamp on successful authentication.
    """
    # Authenticate user
    user = await auth_service.authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    # Create access token
    access_token_expires = timedelta(
        minutes=auth_service.settings.jwt_access_token_expire_minutes
    )
    access_token = auth_service.create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires,
    )

    # Update last login timestamp
    await auth_service.update_last_login(user.id)

    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)) -> dict:
    """Logout endpoint.

    Since we're using JWT tokens (stateless), logout is handled client-side
    by deleting the token. This endpoint just confirms authentication works
    and can be used to update last_login timestamp.
    """
    # Update last login timestamp on logout as well
    # This could be used for tracking last activity
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get current authenticated user information."""
    return current_user


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_create: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Register a new user account.

    Password requirements:
    - At least 8 characters
    - At least one lowercase letter
    - At least one uppercase letter
    - At least one digit
    - At least one special character
    """
    return await auth_service.create_user(user_create)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_admin_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> list[User]:
    """List all users (admin only)."""
    from sqlalchemy import select

    result = await auth_service.db.execute(select(User))
    return list(result.scalars().all())
