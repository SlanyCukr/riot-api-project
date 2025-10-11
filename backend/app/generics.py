"""Generic type definitions and base classes for reusable components."""

from typing import Generic, TypeVar, Dict, List, Optional, Any, Union, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime, timedelta

# Generic type variables
T = TypeVar("T")
TKey = TypeVar("TKey")
TValue = TypeVar("TValue")
TModel = TypeVar("TModel")
TCreate = TypeVar("TCreate")
TUpdate = TypeVar("TUpdate")
TResponse = TypeVar("TResponse")
TRequest = TypeVar("TRequest")


@dataclass
class PaginatedResult(Generic[T]):
    """Generic paginated result container."""

    items: List[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(
        cls, items: List[T], total: int, page: int, size: int
    ) -> "PaginatedResult[T]":
        """Create a paginated result."""
        pages = (total + size - 1) // size if size > 0 else 0
        return cls(items=items, total=total, page=page, size=size, pages=pages)


@dataclass
class APIResponse(Generic[T]):
    """Generic API response wrapper."""

    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    @classmethod
    def success_response(
        cls, data: T, message: Optional[str] = None
    ) -> "APIResponse[T]":
        """Create a success response."""
        return cls(success=True, data=data, message=message)

    @classmethod
    def error_response(
        cls, error: str, message: Optional[str] = None
    ) -> "APIResponse[T]":
        """Create an error response."""
        return cls(success=False, error=error, message=message)


@dataclass
class CacheEntry(Generic[T]):
    """Generic cache entry with metadata."""

    key: str
    value: T
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if the cache entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def access(self) -> T:
        """Mark entry as accessed and return value."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
        return self.value


class OperationResult(Enum):
    """Generic operation result enum."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    NOT_FOUND = "not_found"
    ALREADY_EXISTS = "already_exists"
    INVALID_INPUT = "invalid_input"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMITED = "rate_limited"


@dataclass
class Result(Generic[T]):
    """Generic result wrapper with operation status."""

    status: OperationResult
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @property
    def is_success(self) -> bool:
        """Check if operation was successful."""
        return self.status == OperationResult.SUCCESS

    @property
    def is_failure(self) -> bool:
        """Check if operation failed."""
        return self.status in [OperationResult.FAILURE, OperationResult.INVALID_INPUT]

    @classmethod
    def success(cls, data: T, metadata: Optional[Dict[str, Any]] = None) -> "Result[T]":
        """Create a success result."""
        return cls(status=OperationResult.SUCCESS, data=data, metadata=metadata)

    @classmethod
    def failure(
        cls, error: str, metadata: Optional[Dict[str, Any]] = None
    ) -> "Result[T]":
        """Create a failure result."""
        return cls(status=OperationResult.FAILURE, error=error, metadata=metadata)


class BaseRepository(Generic[TModel, TCreate, TUpdate], ABC):
    """Generic base repository with common CRUD operations."""

    @abstractmethod
    async def get(self, id: int) -> Optional[TModel]:
        """Get entity by ID."""
        ...

    @abstractmethod
    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[TModel]:
        """Get multiple entities with pagination."""
        ...

    @abstractmethod
    async def create(self, obj_in: TCreate) -> TModel:
        """Create new entity."""
        ...

    @abstractmethod
    async def update(
        self, db_obj: TModel, obj_in: Union[TUpdate, Dict[str, Any]]
    ) -> TModel:
        """Update existing entity."""
        ...

    @abstractmethod
    async def delete(self, id: int) -> Optional[TModel]:
        """Delete entity by ID."""
        ...


class BaseService(Generic[TModel, TCreate, TUpdate, TResponse], ABC):
    """Generic base service with common business logic."""

    def __init__(self, repository: BaseRepository[TModel, TCreate, TUpdate]):
        """Initialize service with repository."""
        self.repository = repository

    @abstractmethod
    async def get(self, id: int) -> Optional[TResponse]:
        """Get entity by ID and return response."""
        ...

    @abstractmethod
    async def get_multi(
        self, skip: int = 0, limit: int = 100
    ) -> PaginatedResult[TResponse]:
        """Get multiple entities with pagination."""
        ...

    @abstractmethod
    async def create(self, obj_in: TCreate) -> TResponse:
        """Create new entity and return response."""
        ...

    @abstractmethod
    async def update(
        self, id: int, obj_in: Union[TUpdate, Dict[str, Any]]
    ) -> Optional[TResponse]:
        """Update existing entity and return response."""
        ...

    @abstractmethod
    async def delete(self, id: int) -> bool:
        """Delete entity by ID and return success status."""
        ...


class Cache(Generic[TKey, TValue]):
    """Generic thread-safe cache implementation."""

    def __init__(
        self, default_ttl: Optional[int] = None, max_size: Optional[int] = None
    ):
        """Initialize cache with optional TTL and size limits."""
        self._cache: Dict[TKey, CacheEntry[TValue]] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key: TKey) -> Optional[TValue]:
        """Get value from cache."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None or entry.is_expired():
                if entry is not None:
                    del self._cache[key]
                return None
            return entry.access()

    async def set(self, key: TKey, value: TValue, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        async with self._lock:
            # Enforce size limit
            if self._max_size and len(self._cache) >= self._max_size:
                # Remove least recently used item
                lru_key = min(
                    self._cache.keys(),
                    key=lambda k: (
                        self._cache[k].last_accessed or datetime.min,
                        self._cache[k].access_count,
                    ),
                )
                del self._cache[lru_key]

            expires_at = None
            if ttl or self._default_ttl:
                ttl_seconds = ttl or self._default_ttl
                if ttl_seconds is not None:
                    expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

            self._cache[key] = CacheEntry(
                key=str(key),
                value=value,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
            )

    async def delete(self, key: TKey) -> bool:
        """Delete key from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed items."""
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)


class EventBus(Generic[T]):
    """Generic event bus for decoupled communication."""

    def __init__(self):
        """Initialize event bus."""
        self._subscribers: Dict[str, List[Callable[[T], Any]]] = {}

    def subscribe(self, event_type: str, handler: Callable[[T], Any]) -> None:
        """Subscribe to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[[T], Any]) -> bool:
        """Unsubscribe from an event type."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                return True
            except ValueError:
                pass
        return False

    async def publish(self, event_type: str, event: T) -> List[Any]:
        """Publish an event to all subscribers."""
        results: List[Any] = []
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(event)
                    else:
                        result = handler(event)
                    results.append(result)
                except Exception as e:
                    # Log error but continue with other handlers
                    print(f"Error in event handler: {e}")
        return results


class RateLimiter(Generic[TKey]):
    """Generic rate limiter implementation."""

    def __init__(self):
        """Initialize rate limiter."""
        self._requests: Dict[TKey, List[datetime]] = {}

    async def is_allowed(self, key: TKey, limit: int, window_seconds: int) -> bool:
        """Check if request is allowed for given key."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)

        if key not in self._requests:
            self._requests[key] = []

        # Remove old requests outside the window
        self._requests[key] = [
            req_time for req_time in self._requests[key] if req_time > window_start
        ]

        # Check if under limit
        if len(self._requests[key]) < limit:
            self._requests[key].append(now)
            return True

        return False

    async def get_remaining_requests(
        self, key: TKey, limit: int, window_seconds: int
    ) -> int:
        """Get remaining allowed requests for key."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)

        if key not in self._requests:
            return limit

        # Count requests in current window
        recent_requests = [
            req_time for req_time in self._requests[key] if req_time > window_start
        ]

        return max(0, limit - len(recent_requests))
