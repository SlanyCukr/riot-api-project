"""Authentication service for user management and JWT tokens."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_global_settings
from .models import User
from .schemas import TokenData, UserCreate

# Password hashing context using Argon2id
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        """Initialize auth service."""
        self.db = db
        self.settings = get_global_settings()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password using Argon2id."""
        return pwd_context.hash(password)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email address."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password."""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        return user

    async def create_user(self, user_create: UserCreate) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = await self.get_user_by_email(user_create.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Create new user
        hashed_password = self.get_password_hash(user_create.password)
        user = User(
            email=user_create.email,
            display_name=user_create.display_name,
            password_hash=hashed_password,
            is_active=True,
            is_admin=False,
            email_verified=False,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def update_last_login(self, user_id: int) -> None:
        """Update the user's last login timestamp."""
        user = await self.get_user_by_id(user_id)
        if user:
            user.last_login = datetime.now(timezone.utc)
            user.updated_at = datetime.now(timezone.utc)
            await self.db.commit()

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.settings.jwt_access_token_expire_minutes
            )

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm,
        )

        return encoded_jwt

    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> User:
        """Get the current authenticated user from JWT token."""
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

        user = await self.get_user_by_id(token_data.user_id)

        if user is None:
            raise credentials_exception

        return user


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Dependency to get auth service instance."""
    return AuthService(db)
