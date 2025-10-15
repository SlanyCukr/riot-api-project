"""Error handling utilities for job execution.

Provides decorators to handle common Riot API errors consistently
across all job types, reducing code duplication and improving maintainability.

Error Handling Strategy:
- Rate limit errors: Always re-raise for retry logic
- Authentication errors: Always re-raise (critical)
- General errors: Re-raise if critical=True, log and return None otherwise
"""

from functools import wraps
from typing import Callable, TypeVar, ParamSpec, Any, Optional
import structlog

from ..riot_api.errors import RateLimitError, AuthenticationError, ForbiddenError

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


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
    - RateLimitError: Always re-raise (let caller handle retry)
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
    """Extract logging context from function arguments.

    :param log_context: Optional function to extract context.
    :param args: Function positional arguments.
    :param kwargs: Function keyword arguments.
    :param func_name: Name of the function being wrapped.
    :returns: Context dictionary for logging.
    """
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


def _handle_rate_limit_error(
    operation: str, error: RateLimitError, context: dict
) -> None:
    """Handle rate limit errors."""
    retry_after = getattr(error, "retry_after", None)
    logger.warning(
        f"Rate limit hit during {operation}",
        retry_after=retry_after,
        **context,
    )
    raise


def _handle_auth_error(operation: str, error: Exception, context: dict) -> None:
    """Handle authentication/authorization errors."""
    logger.error(
        f"Authentication failure during {operation} - job cannot continue",
        error=str(error),
        error_type=type(error).__name__,
        **context,
    )
    raise


def _handle_general_error(
    operation: str, error: Exception, context: dict, critical: bool
) -> None:
    """Handle general errors based on critical flag."""
    logger.error(
        f"Failed to {operation}",
        error=str(error),
        error_type=type(error).__name__,
        **context,
    )
    if critical:
        raise
    # If not critical, return None (caller handles)


def _create_async_wrapper(
    func: Callable, operation: str, critical: bool, log_context: Optional[Callable]
) -> Callable:
    """Create async wrapper for error handling."""

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        context = _extract_log_context(log_context, args, kwargs, func.__name__)

        try:
            return await func(*args, **kwargs)
        except RateLimitError as rate_error:
            _handle_rate_limit_error(operation, rate_error, context)
        except (AuthenticationError, ForbiddenError) as auth_error:
            _handle_auth_error(operation, auth_error, context)
        except Exception as error:
            _handle_general_error(operation, error, context, critical)

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
        except RateLimitError as rate_error:
            _handle_rate_limit_error(operation, rate_error, context)
        except (AuthenticationError, ForbiddenError) as auth_error:
            _handle_auth_error(operation, auth_error, context)
        except Exception as error:
            _handle_general_error(operation, error, context, critical)

    return sync_wrapper
