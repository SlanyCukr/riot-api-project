"""Rate limiting implementation for Riot API using response headers."""

import asyncio
import time
from typing import Dict, Optional
import structlog

from .endpoints import parse_rate_limit_header, parse_rate_count_header

logger = structlog.get_logger(__name__)


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded."""

    pass


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

        Raises:
            RateLimitExceededError: If we're out of requests and need to wait
        """
        async with self.lock:
            now = time.time()

            # Check app-level limit
            if self.app_remaining is not None and self.app_remaining <= 0:
                if self.app_reset_time and self.app_reset_time > now:
                    wait_time = self.app_reset_time - now
                    logger.info(
                        "App rate limit reached, waiting",
                        wait_time=wait_time,
                        remaining=self.app_remaining,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    # Reset time passed, reset counter
                    self.app_remaining = None
                    self.app_reset_time = None

            # Check method-level limit
            endpoint_key = self._get_endpoint_key(endpoint, method)
            if endpoint_key in self.method_remaining:
                remaining = self.method_remaining[endpoint_key]
                reset_time = self.method_reset_time.get(endpoint_key)

                if remaining is not None and remaining <= 0:
                    if reset_time and reset_time > now:
                        wait_time = reset_time - now
                        logger.info(
                            "Method rate limit reached, waiting",
                            endpoint=endpoint_key,
                            wait_time=wait_time,
                            remaining=remaining,
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        # Reset time passed, reset counter
                        self.method_remaining[endpoint_key] = None
                        self.method_reset_time[endpoint_key] = None

            # Request spacing to avoid bursts
            time_since_last = now - self.last_request_time
            if time_since_last < self.request_spacing:
                await asyncio.sleep(self.request_spacing - time_since_last)

            self.last_request_time = time.time()

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
            # Parse app rate limits
            app_rate_limit = headers.get("X-App-Rate-Limit", "")
            app_rate_count = headers.get("X-App-Rate-Limit-Count", "")

            if app_rate_limit and app_rate_count:
                limits = parse_rate_limit_header(app_rate_limit)
                counts = parse_rate_count_header(app_rate_count)

                # Use the shortest time window for conservative limiting
                if limits and counts:
                    # Format: "20:1,100:120" -> [(requests, window), ...]
                    # Count:  "15:1,80:120"  -> [(used, window), ...]
                    # We want remaining for shortest window
                    for limit, count in zip(limits, counts):
                        limit_requests = limit["requests"]
                        used_requests = count["requests"]
                        window = limit["window"]

                        remaining = limit_requests - used_requests
                        reset_time = time.time() + window

                        # Update if this is more restrictive
                        if self.app_remaining is None or remaining < self.app_remaining:
                            self.app_remaining = remaining
                            self.app_reset_time = reset_time

                        logger.debug(
                            "Updated app rate limit",
                            limit=limit_requests,
                            used=used_requests,
                            remaining=remaining,
                            window=window,
                        )

            # Parse method rate limits
            method_rate_limit = headers.get("X-Method-Rate-Limit", "")
            method_rate_count = headers.get("X-Method-Rate-Limit-Count", "")

            if method_rate_limit and method_rate_count:
                limits = parse_rate_limit_header(method_rate_limit)
                counts = parse_rate_count_header(method_rate_count)

                endpoint_key = self._get_endpoint_key(endpoint, method)

                if limits and counts:
                    for limit, count in zip(limits, counts):
                        limit_requests = limit["requests"]
                        used_requests = count["requests"]
                        window = limit["window"]

                        remaining = limit_requests - used_requests
                        reset_time = time.time() + window

                        # Update if this is more restrictive
                        current_remaining = self.method_remaining.get(endpoint_key)
                        if current_remaining is None or remaining < current_remaining:
                            self.method_remaining[endpoint_key] = remaining
                            self.method_reset_time[endpoint_key] = reset_time

                        logger.debug(
                            "Updated method rate limit",
                            endpoint=endpoint_key,
                            limit=limit_requests,
                            used=used_requests,
                            remaining=remaining,
                            window=window,
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
