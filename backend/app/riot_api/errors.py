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

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        return {
            "error": "RiotAPIError",
            "message": self.message,
            "status_code": self.status_code,
            "retry_after": self.retry_after,
            "app_rate_limit": self.app_rate_limit,
            "method_rate_limit": self.method_rate_limit,
            "response_data": self.response_data,
        }

    # Helper methods for error type checking
    def is_rate_limit(self) -> bool:
        """Check if this is a rate limit error (429)."""
        return self.status_code == 429

    def is_not_found(self) -> bool:
        """Check if this is a not found error (404)."""
        return self.status_code == 404

    def is_auth_error(self) -> bool:
        """Check if this is an authentication/authorization error (401, 403)."""
        return self.status_code in (401, 403)

    def is_server_error(self) -> bool:
        """Check if this is a server error (5xx)."""
        return self.status_code is not None and self.status_code >= 500

    def is_bad_request(self) -> bool:
        """Check if this is a bad request error (400)."""
        return self.status_code == 400


# Backwards compatibility aliases (deprecated)
RateLimitError = RiotAPIError
AuthenticationError = RiotAPIError
ForbiddenError = RiotAPIError
NotFoundError = RiotAPIError
ServiceUnavailableError = RiotAPIError
BadRequestError = RiotAPIError
