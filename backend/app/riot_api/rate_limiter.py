"""Rate limiting implementation for Riot API using response headers."""

import asyncio
import time
from typing import Dict, Optional
import structlog

from .endpoints import parse_rate_limit_header, parse_rate_count_header

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Header-based rate limiter that trusts Riot API response headers."""

    def __init__(self):
        """Initialize rate limiter."""
        # Track remaining requests from headers
        self.app_remaining: Optional[int] = None
        self.app_reset_time: Optional[float] = None
        self.method_remaining: Dict[str, Optional[int]] = {}
        self.method_reset_time: Dict[str, Optional[float]] = {}

        # Request spacing to avoid bursts
        self.last_request_time = 0
        self.request_spacing = 0.05  # 50ms between requests

        # Lock for thread safety
        self.lock = asyncio.Lock()

    async def wait_if_needed(self, endpoint: str, method: str = "GET") -> None:
        """
        Wait if rate limits would be exceeded based on headers.

        Args:
            endpoint: API endpoint being called
            method: HTTP method being used
        """
        async with self.lock:
            now = time.time()

            # Check app-level limit
            should_reset = await self._check_and_wait_for_limit(
                self.app_remaining, self.app_reset_time, now, "App"
            )
            if should_reset:
                self.app_remaining = None
                self.app_reset_time = None

            # Check method-level limit
            endpoint_key = self._get_endpoint_key(endpoint, method)
            if endpoint_key in self.method_remaining:
                remaining = self.method_remaining[endpoint_key]
                reset_time = self.method_reset_time.get(endpoint_key)

                should_reset = await self._check_and_wait_for_limit(
                    remaining, reset_time, now, "Method", endpoint_key
                )
                if should_reset:
                    self.method_remaining[endpoint_key] = None
                    self.method_reset_time[endpoint_key] = None

            # Request spacing to avoid bursts
            time_since_last = now - self.last_request_time
            if time_since_last < self.request_spacing:
                await asyncio.sleep(self.request_spacing - time_since_last)

            self.last_request_time = time.time()

    async def _check_and_wait_for_limit(
        self,
        remaining: Optional[int],
        reset_time: Optional[float],
        now: float,
        scope_name: str,
        endpoint_key: Optional[str] = None,
    ) -> bool:
        """
        Check if rate limit is exceeded and wait if needed.

        Args:
            remaining: Number of requests remaining
            reset_time: Time when limit resets
            now: Current time
            scope_name: Name of the scope for logging (e.g., "App", "Method")
            endpoint_key: Optional endpoint key for method-scoped limits

        Returns:
            True if limit was reset, False otherwise
        """
        if remaining is not None and remaining <= 0:
            if reset_time and reset_time > now:
                wait_time = reset_time - now
                logger.info(
                    f"{scope_name} rate limit reached, waiting",
                    wait_time=wait_time,
                    remaining=remaining,
                    endpoint=endpoint_key,
                )
                await asyncio.sleep(wait_time)
                return False
            else:
                # Reset time passed, reset counter
                return True
        return False

    def _get_endpoint_key(self, endpoint: str, method: str) -> str:
        """Generate a key for the endpoint."""
        stripped = endpoint.replace("https://", "").replace("http://", "")
        path = stripped.split("/", 1)[1] if "/" in stripped else stripped
        segments = [segment for segment in path.split("/") if segment]

        if segments:
            service_key = "-".join(segments[:4])
        else:
            service_key = path

        return f"{method}:{service_key}"

    def _update_app_limit(self, remaining: int, reset_time: float) -> None:
        """Update application-wide rate limit if more restrictive."""
        if self.app_remaining is None or remaining < self.app_remaining:
            self.app_remaining = remaining
            self.app_reset_time = reset_time

    def _update_method_limit(
        self, endpoint_key: str, remaining: int, reset_time: float
    ) -> None:
        """Update method-specific rate limit if more restrictive."""
        current = self.method_remaining.get(endpoint_key)
        if current is None or remaining < current:
            self.method_remaining[endpoint_key] = remaining
            self.method_reset_time[endpoint_key] = reset_time

    def _process_rate_limit_pair(
        self,
        limit_header: str,
        count_header: str,
        scope: str,
        endpoint_key: str | None = None,
    ) -> None:
        """
        Process a pair of rate limit headers and update internal state.

        Args:
            limit_header: Rate limit header value (e.g., "20:1,100:120")
            count_header: Rate count header value (e.g., "15:1,80:120")
            scope: Either "app" or "method" for logging
            endpoint_key: Endpoint key for method-scoped limits
        """
        if not limit_header or not count_header:
            return

        limits = parse_rate_limit_header(limit_header)
        counts = parse_rate_count_header(count_header)

        if not limits or not counts:
            return

        for limit, count in zip(limits, counts):
            limit_requests = limit["requests"]
            used_requests = count["requests"]
            window = limit["window"]

            remaining = limit_requests - used_requests
            reset_time = time.time() + window

            # Update appropriate scope
            if scope == "app":
                self._update_app_limit(remaining, reset_time)
            elif endpoint_key:  # method scope
                self._update_method_limit(endpoint_key, remaining, reset_time)

            logger.debug(
                f"Updated {scope} rate limit",
                endpoint=endpoint_key if scope == "method" else None,
                limit=limit_requests,
                used=used_requests,
                remaining=remaining,
                window=window,
            )

    def update_limits(
        self, headers: Dict[str, str], endpoint: str, method: str = "GET"
    ) -> None:
        """
        Update rate limits from Riot API response headers.

        Args:
            headers: Response headers containing rate limit info
            endpoint: API endpoint that was called
            method: HTTP method used
        """
        try:
            # Process app rate limits
            self._process_rate_limit_pair(
                headers.get("X-App-Rate-Limit", ""),
                headers.get("X-App-Rate-Limit-Count", ""),
                scope="app",
            )

            # Process method rate limits
            endpoint_key = self._get_endpoint_key(endpoint, method)
            self._process_rate_limit_pair(
                headers.get("X-Method-Rate-Limit", ""),
                headers.get("X-Method-Rate-Limit-Count", ""),
                scope="method",
                endpoint_key=endpoint_key,
            )

        except Exception as e:
            logger.warning(
                "Failed to parse rate limit headers",
                error=str(e),
                headers={
                    k: v
                    for k, v in headers.items()
                    if k.startswith("X-App-Rate") or k.startswith("X-Method-Rate")
                },
            )

    async def record_success(self, endpoint: str, method: str = "GET") -> None:
        """
        Record a successful request.

        Note: With header-based approach, this is a no-op since headers
        provide the truth about remaining requests.
        """
        pass
