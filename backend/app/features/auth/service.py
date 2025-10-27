"""User authentication and management service.

Maintains exact same API as current service,
just converts internals to SQLModel patterns.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import structlog

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_global_settings
from .models_sqlmodel import User, UserCreate, UserPublic, TokenData

logger = structlog.get_logger()

# Password hashing context using Argon2id
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using Argon2id."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    settings = get_global_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt


class AuthService:
    """User authentication and management service."""

    def __init__(self):
        """Initialize auth service."""
        self.settings = get_global_settings()

    async def authenticate_user(
        self, email: str, password: str, db: AsyncSession
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
            HTTPException: If credentials are invalid
        """
        result = await db.execute(select(User).where(User.email == email))
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
        user.last_login = datetime.now(timezone.utc)
        db.add(user)
        await db.commit()

        logger.info("auth_success", email=email, user_id=user.id)
        return UserPublic.model_validate(user)

    async def create_user(self, user_data: UserCreate, db: AsyncSession) -> UserPublic:
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
        existing = await db.execute(select(User).where(User.email == user_data.email))
        if existing.scalar_one_or_none():
            raise ValueError(f"Email {user_data.email} already registered")

        # Create user with hashed password
        user = User(
            email=user_data.email,
            display_name=user_data.display_name,
            password_hash=get_password_hash(user_data.password),
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info("user_created", email=user.email, user_id=user.id)
        return UserPublic.model_validate(user)

    async def get_user_by_id(
        self, user_id: int, db: AsyncSession
    ) -> Optional[UserPublic]:
        """
        Get user by ID.

        Args:
            user_id: User's primary key
            db: Database session

        Returns:
            UserPublic if found, None otherwise
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return None

        return UserPublic.model_validate(user)

    async def get_user_by_email(
        self, email: str, db: AsyncSession
    ) -> Optional[UserPublic]:
        """
        Get user by email.

        Args:
            email: User's email address
            db: Database session

        Returns:
            UserPublic if found, None otherwise
        """
        result = await db.execute(select(User).where(User.email == email))
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

    async def login_user(self, email: str, password: str, db: AsyncSession):
        """
        Authenticate user and return JWT token.

        Args:
            email: User email
            password: User password
            db: Database session

        Returns:
            JWT token for authenticated user

        Raises:
            HTTPException: If authentication fails
        """
        from .models_sqlmodel import Token  # Import here to avoid circular imports

        user_public = await self.authenticate_user(email, password, db)

        if not user_public:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        access_token = self.create_access_token(user_public)
        return Token(access_token=access_token, token_type="bearer")  # nosec B106,B105

    async def get_current_user(self, token: str, db: AsyncSession) -> Optional[User]:
        """Get the current authenticated user from JWT token.

        Args:
            token: JWT token from Authorization header
            db: Database session to fetch user

        Returns:
            User object if authentication successful, None otherwise

        Raises:
            HTTPException: If token is invalid or user not found
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm],
            )
            email: str = payload.get("sub")
            user_id: int = payload.get("user_id")

            if email is None or user_id is None:
                raise credentials_exception

            token_data = TokenData(email=email, user_id=user_id)
        except JWTError:
            raise credentials_exception

        # Fetch user from database using both email and user_id for security
        result = await db.execute(
            select(User).where(
                User.email == token_data.email,
                User.id == token_data.user_id,
                User.is_active,
            )
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise credentials_exception

        return user


def get_auth_service() -> AuthService:
    """Dependency to get auth service instance."""
    return AuthService()
