"""
Service layer decorators for common functionality.

This module provides decorators for error handling, logging, and other
cross-cutting concerns in the service layer.
"""

import functools
import inspect
import structlog
from typing import Any, Callable, Dict, Optional, Type, ParamSpec, TypeVar

from app.core.exceptions import (
    DatabaseError,
    ExternalServiceError,
    ServiceException,
    ValidationError,
)
from app.core.riot_api.errors import (
    RiotAPIError,
    RateLimitError,
    AuthenticationError,
    ForbiddenError,
)

logger = structlog.get_logger(__name__)

# Type variables for generic decorator typing
P = ParamSpec("P")
R = TypeVar("R")


def service_error_handler(
    service_name: str,
    reraise: bool = True,
    include_context: bool = True,
    default_error_type: Type[ServiceException] = ServiceException,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator for handling service method errors with structured logging.

    This decorator catches exceptions, logs them with structured context,
    and optionally re-raises them as service-specific exceptions.

    :param service_name: Name of the service (e.g., "PlayerService")
    :param reraise: Whether to re-raise exceptions after logging
    :param include_context: Whether to include method parameters in error context
    :param default_error_type: Default exception type to wrap generic errors
    :returns: Decorated function with error handling

    :example:
        @service_error_handler("PlayerService")
        async def get_player(self, puuid: str) -> PlayerResponse:
            # Method implementation
            pass
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        operation_name = func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Extract method signature for context
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Create context for logging
            context: Dict[str, Any] = {
                "service": service_name,
                "operation": operation_name,
            }

            if include_context:
                # Add method parameters to context (excluding self and database sessions)
                for name, value in bound_args.arguments.items():
                    if name not in ["self", "db", "session"]:
                        # Limit string values to avoid huge log entries
                        if isinstance(value, str) and len(value) > 100:
                            context[name] = value[:100] + "..."
                        else:
                            context[name] = (
                                str(value)[:200] if value is not None else None
                            )

            try:
                # Log method entry
                logger.debug(
                    "Service method called",
                    **context,
                )

                # Execute the method
                result = await func(*args, **kwargs)

                # Log successful completion
                logger.debug(
                    "Service method completed successfully",
                    **context,
                )

                return result

            except (
                RateLimitError,
                AuthenticationError,
                ForbiddenError,
                RiotAPIError,
            ) as e:
                # Riot API errors must propagate to job handlers unchanged
                # They need special handling (rate limits = graceful stop, auth = fail immediately)
                logger.warning(
                    "Riot API error in service operation - propagating to caller",
                    error_type=e.__class__.__name__,
                    error_message=str(e),
                    status_code=getattr(e, "status_code", None),
                    **context,
                )
                raise  # Always re-raise so job error handler can process it

            except ServiceException as e:
                # Already a service exception - log and re-raise
                logger.error(
                    "Service operation failed",
                    error_type=e.__class__.__name__,
                    error_message=str(e),
                    error_context=e.context,
                    **context,
                )
                if reraise:
                    raise
                return None  # type: ignore[return-value]

            except ValueError as e:
                # Input validation error
                validation_error = ValidationError(
                    message=str(e),
                    service=service_name,
                    operation=operation_name,
                    context=context if include_context else {},
                )
                logger.error(
                    "Validation error in service operation",
                    error_message=str(e),
                    **context,
                )
                if reraise:
                    raise validation_error
                return None  # type: ignore[return-value]

            except (ConnectionError, TimeoutError) as e:
                # External service connectivity issues
                external_error = ExternalServiceError(
                    message=str(e),
                    service=service_name,
                    operation=operation_name,
                    context=context if include_context else {},
                    original_error=e,
                )
                logger.error(
                    "External service connectivity error",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    **context,
                )
                if reraise:
                    raise external_error
                return None  # type: ignore[return-value]

            except Exception as e:
                # Generic database or unexpected error
                error_message = (
                    f"Unexpected error in {service_name}.{operation_name}: {str(e)}"
                )

                # Check if it's likely a database error
                if any(
                    keyword in str(e).lower()
                    for keyword in ["database", "sql", "connection", "transaction"]
                ):
                    error = DatabaseError(
                        message=str(e),
                        service=service_name,
                        operation=operation_name,
                        context=context if include_context else {},
                        original_error=e,
                    )
                else:
                    error = default_error_type(
                        message=error_message,
                        service=service_name,
                        operation=operation_name,
                        context=context if include_context else {},
                        original_error=e,
                    )

                logger.error(
                    "Unexpected error in service operation",
                    error_type=e.__class__.__name__,
                    error_message=str(e),
                    error_details=getattr(e, "details", None),
                    **context,
                )

                if reraise:
                    raise error
                return None  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # For synchronous methods (unlikely in this async codebase but included for completeness)
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            context: Dict[str, Any] = {
                "service": service_name,
                "operation": operation_name,
            }

            if include_context:
                for name, value in bound_args.arguments.items():
                    if name not in ["self", "db", "session"]:
                        if isinstance(value, str) and len(value) > 100:
                            context[name] = value[:100] + "..."
                        else:
                            context[name] = (
                                str(value)[:200] if value is not None else None
                            )

            try:
                logger.debug(
                    "Service method called",
                    **context,
                )

                result = func(*args, **kwargs)

                logger.debug(
                    "Service method completed successfully",
                    **context,
                )

                return result

            except Exception as e:
                # Similar error handling as async version
                logger.error(
                    "Error in synchronous service operation",
                    error_type=e.__class__.__name__,
                    error_message=str(e),
                    **context,
                )

                if reraise:
                    raise
                return None  # type: ignore[return-value]

        # Return appropriate wrapper based on whether function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        else:
            return sync_wrapper  # type: ignore[return-value]

    return decorator


def input_validation(
    validate_non_empty: Optional[list[str]] = None,
    validate_positive: Optional[list[str]] = None,
    custom_validators: Optional[Dict[str, Callable[[Any], None]]] = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator for input validation in service methods.

    :param validate_non_empty: List of parameter names that must not be empty
    :param validate_positive: List of parameter names that must be positive numbers
    :param custom_validators: Dictionary of parameter_name -> validator_function

    :example:
        @input_validation(
            validate_non_empty=["puuid", "platform"],
            validate_positive=["limit"],
        )
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Perform validations
            if validate_non_empty:
                for param_name in validate_non_empty:
                    if param_name in bound_args.arguments:
                        value = bound_args.arguments[param_name]
                        if value is None or (
                            isinstance(value, str) and not value.strip()
                        ):
                            raise ValueError(f"{param_name} cannot be empty or None")

            if validate_positive:
                for param_name in validate_positive:
                    if param_name in bound_args.arguments:
                        value = bound_args.arguments[param_name]
                        if isinstance(value, (int, float)) and value <= 0:
                            raise ValueError(f"{param_name} must be positive")

            if custom_validators:
                for param_name, validator in custom_validators.items():
                    if param_name in bound_args.arguments:
                        value = bound_args.arguments[param_name]
                        if value is not None:
                            validator(value)

            return await func(*args, **kwargs)

        @functools.wraps(wrapper)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Synchronous version for completeness
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Same validations as async version
            if validate_non_empty:
                for param_name in validate_non_empty:
                    if param_name in bound_args.arguments:
                        value = bound_args.arguments[param_name]
                        if value is None or (
                            isinstance(value, str) and not value.strip()
                        ):
                            raise ValueError(f"{param_name} cannot be empty or None")

            if validate_positive:
                for param_name in validate_positive:
                    if param_name in bound_args.arguments:
                        value = bound_args.arguments[param_name]
                        if isinstance(value, (int, float)) and value <= 0:
                            raise ValueError(f"{param_name} must be positive")

            if custom_validators:
                for param_name, validator in custom_validators.items():
                    if param_name in bound_args.arguments:
                        value = bound_args.arguments[param_name]
                        if value is not None:
                            validator(value)

            return func(*args, **kwargs)

        # Return appropriate wrapper based on whether function is async
        if inspect.iscoroutinefunction(func):
            return wrapper  # type: ignore[return-value]
        else:
            return sync_wrapper  # type: ignore[return-value]

    return decorator
