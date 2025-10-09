"""Custom error classes for Riot API client."""

from typing import Optional, Dict, Any
import json


class RiotAPIError(Exception):
    """Base exception for Riot API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        retry_after: Optional[float] = None,
    ):
        """Initialize RiotAPIError."""
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}
        self.retry_after = retry_after
        self.message = message

    def __str__(self) -> str:
        """Return string representation of the error."""
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
            "response_data": self.response_data,
        }


class RateLimitError(RiotAPIError):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        app_rate_limit: Optional[str] = None,
        method_rate_limit: Optional[str] = None,
    ):
        """Initialize RateLimitError."""
        super().__init__(message=message, status_code=429, retry_after=retry_after)
        self.app_rate_limit = app_rate_limit
        self.method_rate_limit = method_rate_limit

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.retry_after:
            return (
                f"Rate Limit Error: {self.message} (Retry after: {self.retry_after}s)"
            )
        return f"Rate Limit Error: {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "error": "RateLimitError",
                "app_rate_limit": self.app_rate_limit,
                "method_rate_limit": self.method_rate_limit,
            }
        )
        return base_dict


class AuthenticationError(RiotAPIError):
    """Exception raised for authentication/authorization failures."""

    def __init__(self, message: str = "Authentication failed"):
        """Initialize AuthenticationError."""
        super().__init__(message=message, status_code=401)

    def __str__(self) -> str:
        """Return string representation of the error."""
        return f"Authentication Error: {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        base_dict = super().to_dict()
        base_dict["error"] = "AuthenticationError"
        return base_dict


class ForbiddenError(RiotAPIError):
    """Exception raised when access is forbidden (e.g., deprecated endpoint or insufficient permissions)."""

    def __init__(
        self,
        message: str = "Access forbidden - may be deprecated endpoint or insufficient API key permissions",
    ):
        """Initialize ForbiddenError."""
        super().__init__(message=message, status_code=403)

    def __str__(self) -> str:
        """Return string representation of the error."""
        return f"Forbidden Error: {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        base_dict = super().to_dict()
        base_dict["error"] = "ForbiddenError"
        return base_dict


class NotFoundError(RiotAPIError):
    """Exception raised when requested resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        """Initialize NotFoundError."""
        super().__init__(message=message, status_code=404)

    def __str__(self) -> str:
        """Return string representation of the error."""
        return f"Not Found Error: {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        base_dict = super().to_dict()
        base_dict["error"] = "NotFoundError"
        return base_dict


class ServiceUnavailableError(RiotAPIError):
    """Exception raised when Riot API service is unavailable."""

    def __init__(self, message: str = "API service unavailable"):
        """Initialize ServiceUnavailableError."""
        super().__init__(message=message, status_code=503)

    def __str__(self) -> str:
        """Return string representation of the error."""
        return f"Service Unavailable Error: {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        base_dict = super().to_dict()
        base_dict["error"] = "ServiceUnavailableError"
        return base_dict


class BadRequestError(RiotAPIError):
    """Exception raised for malformed requests."""

    def __init__(self, message: str = "Invalid API request"):
        """Initialize InvalidRequestError."""
        super().__init__(message=message, status_code=400)

    def __str__(self) -> str:
        """Return string representation of the error."""
        return f"Bad Request Error: {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        base_dict = super().to_dict()
        base_dict["error"] = "BadRequestError"
        return base_dict


class CircuitBreakerOpenError(RiotAPIError):
    """Exception raised when circuit breaker is open."""

    def __init__(self, message: str = "Circuit breaker is open"):
        """Initialize CircuitBreakerOpenError."""
        super().__init__(message=message)
        self.status_code = None  # This is a client-side error

    def __str__(self) -> str:
        """Return string representation of the error."""
        return f"CircuitBreakerOpenError: {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        base_dict = super().to_dict()
        base_dict["error"] = "CircuitBreakerOpenError"
        return base_dict


def handle_api_error(status_code: int, response_text: str) -> RiotAPIError:
    """
    Convert HTTP status code and response text to appropriate exception.

    Args:
        status_code: HTTP status code
        response_text: Response body text

    Returns:
        Appropriate RiotAPIError subclass
    """
    try:
        response_data = json.loads(response_text) if response_text else {}
        message = response_data.get("status", {}).get("message", str(response_text))
    except (json.JSONDecodeError, AttributeError):
        message = str(response_text)

    if status_code == 400:
        return BadRequestError(message)
    elif status_code == 401:
        return AuthenticationError(message)
    elif status_code == 403:
        return ForbiddenError(message)
    elif status_code == 404:
        return NotFoundError(message)
    elif status_code == 429:
        retry_after = (
            response_data.get("status", {}).get("retry_after")
            if isinstance(response_data, dict)
            else None
        )
        return RateLimitError(message, retry_after=retry_after)
    elif status_code == 503:
        return ServiceUnavailableError(message)
    elif 500 <= status_code < 600:
        return ServiceUnavailableError(f"Server error: {message}")
    else:
        return RiotAPIError(f"HTTP {status_code}: {message}", status_code=status_code)
