"""Error handling utilities for job execution.

Provides decorators to handle common Riot API errors consistently
across all job types, reducing code duplication and improving maintainability.

Error Handling Strategy:
- Rate limit errors: Convert to RateLimitSignal for graceful handling
- Authentication errors: Always re-raise (critical)
- General errors: Re-raise if critical=True, log and return None otherwise
"""

from functools import wraps
from typing import Callable, TypeVar, ParamSpec, Any, Optional
import structlog

from app.core.riot_api.errors import RateLimitError, AuthenticationError, ForbiddenError

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


class RateLimitSignal(Exception):
    """Signal that a rate limit was hit during job execution.

    This is NOT a failure - it signals that the job should stop gracefully
    and save its progress with a RATE_LIMITED status.

    :param retry_after: Seconds to wait before retrying (from Riot API)
    :param message: Optional message describing the rate limit
    """

    def __init__(
        self, retry_after: Optional[int] = None, message: str = "Rate limit hit"
    ):
        """Initialize rate limit signal.

        :param retry_after: Seconds to wait before retrying
        :param message: Description of rate limit condition
        """
        self.retry_after = retry_after
        self.message = message
        super().__init__(message)


def handle_riot_api_errors(
    *,
    operation: str,
    critical: bool = True,
    log_context: Optional[Callable[..., dict[str, Any]]] = None,
):
    """Decorator to handle common Riot API errors with consistent behavior.

    :param operation: Description of the operation (e.g., "fetch matches").
    :param critical: If True, re-raise all exceptions. If False, log and return None.
    :param log_context: Optional function extracting context from args for logging.
                        Example: lambda self, player: {"puuid": player.puuid}

    Error handling logic:
    - RateLimitError: Convert to RateLimitSignal for graceful job termination
    - AuthenticationError/ForbiddenError: Always re-raise (critical auth failures)
    - Other exceptions: Log error, re-raise if critical=True, otherwise return None

    Usage example::

        @handle_riot_api_errors(
            operation="update player",
            critical=False,
            log_context=lambda self, player: {"puuid": player.puuid}
        )
        async def _sync_tracked_player(self, db: AsyncSession, player: Player):
            # Your implementation here
            pass
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        import inspect

        # Choose wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return _create_async_wrapper(func, operation, critical, log_context)
        return _create_sync_wrapper(func, operation, critical, log_context)

    return decorator


def _extract_log_context(
    log_context: Optional[Callable], args: tuple, kwargs: dict, func_name: str
) -> dict:
    """Extract logging context from function arguments."""
    if not log_context:
        return {}

    try:
        return log_context(*args, **kwargs)
    except Exception as e:
        logger.warning(
            "Failed to extract log context",
            error=str(e),
            function=func_name,
        )
        return {}


def _handle_error(
    error: Exception, operation: str, critical: bool, context: dict
) -> None:
    """Handle exceptions with consistent logging and re-raise logic."""
    if isinstance(error, RateLimitError):
        retry_after = getattr(error, "retry_after", None)
        logger.warning(
            f"Rate limit hit during {operation}",
            retry_after=retry_after,
            **context,
        )
        # Convert to RateLimitSignal for graceful job termination
        raise RateLimitSignal(
            retry_after=retry_after, message=f"Rate limit hit during {operation}"
        )

    if isinstance(error, (AuthenticationError, ForbiddenError)):
        logger.error(
            f"Authentication failure during {operation} - job cannot continue",
            error=str(error),
            error_type=type(error).__name__,
            **context,
        )
        raise

    logger.error(
        f"Failed to {operation}",
        error=str(error),
        error_type=type(error).__name__,
        **context,
    )
    if critical:
        raise


def _create_async_wrapper(
    func: Callable, operation: str, critical: bool, log_context: Optional[Callable]
) -> Callable:
    """Create async wrapper for error handling."""

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        context = _extract_log_context(log_context, args, kwargs, func.__name__)
        try:
            return await func(*args, **kwargs)
        except RateLimitSignal:
            # Always let RateLimitSignal propagate - it's not an error!
            raise
        except Exception as error:
            _handle_error(error, operation, critical, context)
            return None  # For non-critical errors that don't re-raise

    return async_wrapper


def _create_sync_wrapper(
    func: Callable, operation: str, critical: bool, log_context: Optional[Callable]
) -> Callable:
    """Create sync wrapper for error handling."""

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        context = _extract_log_context(log_context, args, kwargs, func.__name__)
        try:
            return func(*args, **kwargs)
        except RateLimitSignal:
            # Always let RateLimitSignal propagate - it's not an error!
            raise
        except Exception as error:
            _handle_error(error, operation, critical, context)
            return None  # For non-critical errors that don't re-raise

    return sync_wrapper
