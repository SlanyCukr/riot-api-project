"""Protocol definitions for common service interfaces in the application."""

from typing import Protocol, TypeVar, Generic, Any, Dict, List, Optional, AsyncGenerator
from abc import abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession


# Generic type variables
T_contra = TypeVar("T_contra", contravariant=True)
T_co = TypeVar("T_co", covariant=True)
T = TypeVar("T")
T_covariant = TypeVar("T_covariant", covariant=True)
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", contravariant=True)
UpdateSchemaType = TypeVar("UpdateSchemaType", contravariant=True)


class DatabaseService(Protocol, Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Protocol for database service operations."""

    @abstractmethod
    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        """Get a record by ID."""
        ...

    @abstractmethod
    async def get_multi(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records with pagination."""
        ...

    @abstractmethod
    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        ...

    @abstractmethod
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Any,
        obj_in: UpdateSchemaType | Dict[str, Any],
    ) -> Any:
        """Update an existing record."""
        ...

    @abstractmethod
    async def delete(self, db: AsyncSession, *, id: int) -> Optional[ModelType]:
        """Delete a record by ID."""
        ...


class APIClient(Protocol):
    """Protocol for API client implementations."""

    @abstractmethod
    async def get(self, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        """Make a GET request to the API."""
        ...

    @abstractmethod
    async def post(self, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        """Make a POST request to the API."""
        ...


class Cacheable(Protocol):
    """Protocol for cacheable services."""

    @abstractmethod
    async def get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        ...

    @abstractmethod
    async def set_cached(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        ...

    @abstractmethod
    async def invalidate_cache(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern."""
        ...


class DataManager(Protocol):
    """Protocol for data management operations."""

    @abstractmethod
    async def ensure_fresh_data(
        self,
        puuid: str,
        data_type: str,
        fetch_func: Any,
        cache_key: Optional[str] = None,
        max_age_minutes: int = 60,
    ) -> Any:
        """Ensure data is fresh, fetching if needed."""
        ...

    @abstractmethod
    async def get_freshness_status(self, puuid: str, data_type: str) -> Dict[str, Any]:
        """Get data freshness status."""
        ...


class DetectionAlgorithm(Protocol):
    """Protocol for smurf detection algorithms."""

    @abstractmethod
    async def analyze(self, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze player data for smurf detection."""
        ...

    @abstractmethod
    def get_confidence_score(self, analysis_result: Dict[str, Any]) -> float:
        """Get confidence score from analysis result."""
        ...


class MetricsCollector(Protocol):
    """Protocol for metrics collection."""

    @abstractmethod
    def increment_counter(
        self, metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter metric."""
        ...

    @abstractmethod
    def record_timing(
        self,
        metric_name: str,
        duration_ms: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a timing metric."""
        ...

    @abstractmethod
    def set_gauge(
        self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge metric."""
        ...


class RateLimiter(Protocol):
    """Protocol for rate limiting."""

    @abstractmethod
    async def acquire(self, key: str, limit: int, window: int) -> bool:
        """Acquire a rate limit token."""
        ...

    @abstractmethod
    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed."""
        ...


class Configurable(Protocol):
    """Protocol for configurable components."""

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the component with settings."""
        ...

    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        ...


class AsyncIterator(Protocol, Generic[T_covariant]):
    """Protocol for async iterators."""

    @abstractmethod
    def __aiter__(self) -> AsyncGenerator[T_covariant, None]:
        """Return async iterator."""
        ...


class Validator(Protocol, Generic[T_covariant]):
    """Protocol for data validation."""

    @abstractmethod
    def validate(self, data: Any) -> T_covariant:
        """Validate data and return typed result."""
        ...

    @abstractmethod
    def is_valid(self, data: Any) -> bool:
        """Check if data is valid."""
        ...


class Serializer(Protocol, Generic[T_contra, T_co]):
    """Protocol for data serialization."""

    @abstractmethod
    def serialize(self, obj: T_contra) -> Dict[str, Any]:
        """Serialize object to dictionary."""
        ...

    @abstractmethod
    def deserialize(self, data: Dict[str, Any]) -> T_co:
        """Deserialize dictionary to object."""
        ...
