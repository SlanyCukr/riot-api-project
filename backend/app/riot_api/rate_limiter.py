"""
Rate limiting implementation for Riot API with exponential backoff.
"""

import asyncio
import time
import random
from collections import deque
from typing import Dict, List, Optional, Any
import structlog

from .endpoints import parse_rate_limit_header, parse_rate_count_header, RateLimitInfo

logger = structlog.get_logger(__name__)


class RateLimitTracker:
    """Track rate limits for a specific limit set."""

    def __init__(self, requests: int, window: int):
        """
        Initialize rate limit tracker.

        Args:
            requests: Maximum requests allowed
            window: Time window in seconds
        """
        self.requests = requests
        self.window = window
        self.timestamps: deque[float] = deque()

    def can_make_request(self, now: float) -> bool:
        """Check if a request can be made."""
        # Remove expired timestamps
        cutoff = now - self.window
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

        return len(self.timestamps) < self.requests

    def record_request(self, now: float) -> None:
        """Record a request was made."""
        self.timestamps.append(now)

    def get_wait_time(self, now: float) -> float:
        """Get time to wait until next request can be made."""
        if self.can_make_request(now):
            return 0

        # Return time until oldest request expires
        return self.timestamps[0] + self.window - now

    def get_current_usage(self, now: float) -> int:
        """Get current request usage."""
        cutoff = now - self.window
        return sum(1 for ts in self.timestamps if ts >= cutoff)


class CircuitBreaker:
    """Circuit breaker for handling repeated failures."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open
        self.lock = asyncio.Lock()

    async def before_request(self) -> bool:
        """
        Check if request should be allowed.

        Returns:
            True if request should be allowed, False if circuit is open
        """
        async with self.lock:
            now = time.time()

            if self.state == "closed":
                return True
            elif self.state == "open":
                # Check if recovery timeout has passed
                if now - self.last_failure_time >= self.recovery_timeout:
                    self.state = "half-open"
                    self.failure_count = 0
                    return True
                return False
            elif self.state == "half-open":
                return True

            return False

    async def on_success(self) -> None:
        """Handle successful request."""
        async with self.lock:
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0

    async def on_failure(self) -> None:
        """Handle failed request."""
        async with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if (
                self.state == "closed" and self.failure_count >= self.failure_threshold
            ) or (self.state == "half-open"):
                self.state = "open"


class RateLimiter:
    """Multi-level rate limiter with exponential backoff and circuit breaker."""

    def __init__(self):
        """Initialize rate limiter."""
        # App-level rate limit trackers
        self.app_limiters: Dict[str, RateLimitTracker] = {}

        # Method-level rate limit trackers
        self.method_limiters: Dict[str, RateLimitTracker] = {}

        # Circuit breakers for different error types
        self.circuit_breakers: Dict[str, CircuitBreaker] = {
            "429": CircuitBreaker(failure_threshold=3, recovery_timeout=30),
            "5xx": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
            "timeout": CircuitBreaker(failure_threshold=3, recovery_timeout=45),
        }

        # Request spacing
        self.last_request_time: Dict[str, float] = {}
        self.request_spacing = 0.05  # 50ms between requests (20 requests/second)

        # Retry configuration
        self.max_retries = 3
        self.base_backoff = 1.0
        self.max_backoff = 60.0
        self.jitter_factor = 0.1

        # Lock for thread safety
        self.lock = asyncio.Lock()

        # Initialize default limits
        self._initialize_default_limits()

    def _initialize_default_limits(self) -> None:
        """Initialize default rate limits."""
        app_limits = RateLimitInfo.get_app_limits()
        for limit_name, limit_info in app_limits.items():
            self.app_limiters[limit_name] = RateLimitTracker(
                limit_info["requests"], limit_info["window"]
            )

    async def wait_if_needed(self, endpoint: str, method: str = "GET") -> None:
        """
        Wait if rate limits would be exceeded.

        Args:
            endpoint: API endpoint being called
            method: HTTP method being used
        """
        async with self.lock:
            now = time.time()

            # Check circuit breakers
            for circuit_name, breaker in self.circuit_breakers.items():
                if not await breaker.before_request():
                    raise Exception(f"Circuit breaker '{circuit_name}' is open")

            # Check app-level limits
            for limit_name, limiter in self.app_limiters.items():
                if not limiter.can_make_request(now):
                    wait_time = limiter.get_wait_time(now)
                    logger.warning(
                        "App rate limit exceeded, waiting",
                        limit_name=limit_name,
                        wait_time=wait_time,
                        current_usage=limiter.get_current_usage(now),
                    )
                    await asyncio.sleep(wait_time)
                    now = time.time()  # Update time after sleep

            # Check method-level limits
            endpoint_key = self._get_endpoint_key(endpoint, method)
            if endpoint_key in self.method_limiters:
                method_limiter = self.method_limiters[endpoint_key]
                if not method_limiter.can_make_request(now):
                    wait_time = method_limiter.get_wait_time(now)
                    logger.warning(
                        "Method rate limit exceeded, waiting",
                        endpoint_key=endpoint_key,
                        wait_time=wait_time,
                        current_usage=method_limiter.get_current_usage(now),
                    )
                    await asyncio.sleep(wait_time)
                    now = time.time()  # Update time after sleep

            # Check request spacing
            if endpoint_key in self.last_request_time:
                time_since = now - self.last_request_time[endpoint_key]
                if time_since < self.request_spacing:
                    sleep_time = self.request_spacing - time_since
                    await asyncio.sleep(sleep_time)
                    now = time.time()  # Update time after sleep

            # Record request
            for limiter in self.app_limiters.values():
                limiter.record_request(now)

            if endpoint_key in self.method_limiters:
                self.method_limiters[endpoint_key].record_request(now)

            self.last_request_time[endpoint_key] = now

    def _get_endpoint_key(self, endpoint: str, method: str) -> str:
        """Generate a key for the endpoint."""
        # Extract the main endpoint path for rate limiting
        parts = endpoint.split("/")
        if len(parts) >= 4:
            # Use the main service and endpoint (e.g., "lol-match-v5-matches")
            service_key = f"{parts[-3]}-{parts[-2]}-{parts[-1]}"
        else:
            service_key = endpoint

        return f"{method}:{service_key}"

    def update_limits(
        self, headers: Dict[str, str], endpoint: str, method: str = "GET"
    ) -> None:
        """
        Update rate limits from response headers.

        Args:
            headers: Response headers
            endpoint: API endpoint that was called
            method: HTTP method used
        """
        try:
            # Parse app rate limits
            app_rate_limit = headers.get("X-App-Rate-Limit", "")
            app_rate_count = headers.get("X-App-Rate-Count", "")

            if app_rate_limit:
                limits = parse_rate_limit_header(app_rate_limit)
                counts = (
                    parse_rate_count_header(app_rate_count) if app_rate_count else []
                )

                self._update_limit_trackers(self.app_limiters, limits, counts, "app")

            # Parse method rate limits
            method_rate_limit = headers.get("X-Method-Rate-Limit", "")
            method_rate_count = headers.get("X-Method-Rate-Count", "")

            if method_rate_limit:
                limits = parse_rate_limit_header(method_rate_limit)
                counts = (
                    parse_rate_count_header(method_rate_count)
                    if method_rate_count
                    else []
                )

                endpoint_key = self._get_endpoint_key(endpoint, method)
                self._update_limit_trackers(
                    self.method_limiters, limits, counts, endpoint_key
                )

        except Exception as e:
            logger.error("Failed to update rate limits", error=str(e), headers=headers)

    def _update_limit_trackers(
        self,
        limiters: Dict[str, RateLimitTracker],
        limits: List[Dict[str, int]],
        counts: List[Dict[str, int]],
        base_key: str,
    ) -> None:
        """Update limit trackers with new limits and counts."""
        for i, limit_info in enumerate(limits):
            key = f"{base_key}_{i}"
            requests = limit_info["requests"]
            window = limit_info["window"]

            # Create or update limiter
            if key not in limiters:
                limiters[key] = RateLimitTracker(requests, window)

            # Update counts if available
            if i < len(counts):
                count = counts[i]["requests"]
                # This is a simplified approach - in production you'd want
                # to track actual usage more precisely
                logger.debug(
                    "Rate limit usage",
                    key=key,
                    count=count,
                    limit=requests,
                    window=window,
                )

    async def handle_429(self, headers: Dict[str, str], endpoint: str) -> float:
        """
        Handle 429 rate limit response.

        Args:
            headers: Response headers
            endpoint: API endpoint that was rate limited

        Returns:
            Time to wait before retrying
        """
        # Use Retry-After header if available
        retry_after = headers.get("Retry-After", "1")
        try:
            wait_time = float(retry_after)
        except ValueError:
            wait_time = 1.0

        # Trigger circuit breaker
        await self.circuit_breakers["429"].on_failure()

        logger.warning(
            "Rate limit hit, waiting",
            endpoint=endpoint,
            wait_time=wait_time,
            retry_after=retry_after,
        )

        return wait_time

    async def calculate_backoff(
        self, attempt: int, base_delay: Optional[float] = None
    ) -> float:
        """
        Calculate exponential backoff with jitter.

        Args:
            attempt: Retry attempt number (0-based)
            base_delay: Base delay time (uses configured default if None)

        Returns:
            Time to wait in seconds
        """
        if base_delay is None:
            base_delay = self.base_backoff

        # Exponential backoff: base_delay * (2 ^ attempt)
        backoff = min(base_delay * (2**attempt), self.max_backoff)

        # Add jitter to prevent thundering herd
        jitter = backoff * self.jitter_factor * (random.random() * 2 - 1)
        total_backoff = max(0, backoff + jitter)

        logger.debug(
            "Calculated backoff",
            attempt=attempt,
            base_delay=base_delay,
            backoff=backoff,
            jitter=jitter,
            total_backoff=total_backoff,
        )

        return total_backoff

    async def record_success(self, endpoint: str, method: str = "GET") -> None:
        """Record a successful request."""
        endpoint_key = self._get_endpoint_key(endpoint, method)

        # Reset circuit breakers on success
        for breaker in self.circuit_breakers.values():
            await breaker.on_success()

        logger.debug("Request successful", endpoint=endpoint_key)

    async def record_failure(
        self,
        endpoint: str,
        method: str = "GET",
        status_code: Optional[int] = None,
        error_type: Optional[str] = None,
    ) -> None:
        """
        Record a failed request.

        Args:
            endpoint: API endpoint that failed
            method: HTTP method used
            status_code: HTTP status code if available
            error_type: Type of error if available
        """
        endpoint_key = self._get_endpoint_key(endpoint, method)

        # Determine circuit breaker to trigger
        circuit_key = "general"
        if status_code == 429:
            circuit_key = "429"
        elif status_code and status_code >= 500:
            circuit_key = "5xx"
        elif error_type == "timeout":
            circuit_key = "timeout"

        if circuit_key in self.circuit_breakers:
            await self.circuit_breakers[circuit_key].on_failure()

        logger.warning(
            "Request failed",
            endpoint=endpoint_key,
            status_code=status_code,
            error_type=error_type,
            circuit_key=circuit_key,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        now = time.time()
        stats = {
            "app_limits": {},
            "method_limits": {},
            "circuit_breakers": {},
            "last_requests": {},
        }

        # App limit stats
        for key, limiter in self.app_limiters.items():
            stats["app_limits"][key] = {
                "current_usage": limiter.get_current_usage(now),
                "max_requests": limiter.requests,
                "window": limiter.window,
                "can_make_request": limiter.can_make_request(now),
                "wait_time": limiter.get_wait_time(now),
            }

        # Method limit stats
        for key, limiter in self.method_limiters.items():
            stats["method_limits"][key] = {
                "current_usage": limiter.get_current_usage(now),
                "max_requests": limiter.requests,
                "window": limiter.window,
                "can_make_request": limiter.can_make_request(now),
                "wait_time": limiter.get_wait_time(now),
            }

        # Circuit breaker stats
        for key, breaker in self.circuit_breakers.items():
            stats["circuit_breakers"][key] = {
                "state": breaker.state,
                "failure_count": breaker.failure_count,
                "last_failure_time": breaker.last_failure_time,
                "time_since_failure": now - breaker.last_failure_time
                if breaker.last_failure_time > 0
                else None,
            }

        # Last request times
        for key, last_time in self.last_request_time.items():
            stats["last_requests"][key] = {
                "last_request": last_time,
                "time_since": now - last_time,
            }

        return stats

    async def reset(self) -> None:
        """Reset all rate limiter state."""
        async with self.lock:
            self.app_limiters.clear()
            self.method_limiters.clear()
            self.last_request_time.clear()

            # Reset circuit breakers
            for breaker in self.circuit_breakers.values():
                breaker.failure_count = 0
                breaker.last_failure_time = 0
                breaker.state = "closed"

            # Reinitialize default limits
            self._initialize_default_limits()

        logger.info("Rate limiter reset")
