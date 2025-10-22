"""Custom error classes for Riot API client."""

from typing import Optional, Dict, Any


class RiotAPIError(Exception):
    """Base exception for Riot API errors with status code tracking."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        retry_after: Optional[float] = None,
        app_rate_limit: Optional[str] = None,
        method_rate_limit: Optional[str] = None,
    ) -> None:
        """
        Initialize RiotAPIError.

        Args:
            message: Error message
            status_code: HTTP status code (400, 401, 403, 404, 429, 503, etc.)
            response_data: Raw response data from API
            retry_after: Seconds to wait before retry (for 429 errors)
            app_rate_limit: App-level rate limit header (for 429 errors)
            method_rate_limit: Method-level rate limit header (for 429 errors)
        """
        super().__init__(message)
        self.status_code: Optional[int] = status_code
        self.response_data: Dict[str, Any] = response_data or {}
        self.retry_after: Optional[float] = retry_after
        self.app_rate_limit: Optional[str] = app_rate_limit
        self.method_rate_limit: Optional[str] = method_rate_limit
        self.message: str = message

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.status_code == 429 and self.retry_after:
            return f"Rate Limit Error {self.status_code}: {self.message} (Retry after: {self.retry_after}s)"
        if self.status_code:
            return f"Riot API Error {self.status_code}: {self.message}"
        return f"Riot API Error: {self.message}"


class RateLimitError(RiotAPIError):
    """Rate limit error (429) - can be retried after cooldown."""

    pass


class AuthenticationError(RiotAPIError):
    """Authentication error (401) - invalid or expired API key."""

    pass


class ForbiddenError(RiotAPIError):
    """Forbidden error (403) - insufficient permissions."""

    pass


class NotFoundError(RiotAPIError):
    """Not found error (404) - resource doesn't exist."""

    pass


class ServiceUnavailableError(RiotAPIError):
    """Service unavailable (503) - Riot servers down."""

    pass


class BadRequestError(RiotAPIError):
    """Bad request (400) - invalid parameters."""

    pass
