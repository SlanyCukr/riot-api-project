"""
Tests for rate limiter.
"""

import pytest
import asyncio
import time

from backend.app.riot_api.rate_limiter import (
    RateLimiter,
    RateLimitTracker,
    CircuitBreaker,
)


class TestRateLimitTracker:
    """Test cases for RateLimitTracker."""

    def test_initialization(self):
        """Test rate limit tracker initialization."""
        tracker = RateLimitTracker(requests=10, window=60)
        assert tracker.requests == 10
        assert tracker.window == 60
        assert len(tracker.timestamps) == 0

    def test_can_make_request_empty(self):
        """Test can make request when tracker is empty."""
        tracker = RateLimitTracker(requests=10, window=60)
        assert tracker.can_make_request(time.time()) is True

    def test_can_make_request_under_limit(self):
        """Test can make request when under limit."""
        tracker = RateLimitTracker(requests=10, window=60)
        now = time.time()

        # Add 9 requests (under limit of 10)
        for i in range(9):
            tracker.record_request(now - i)

        assert tracker.can_make_request(now) is True

    def test_can_make_request_over_limit(self):
        """Test can make request when over limit."""
        tracker = RateLimitTracker(requests=5, window=60)
        now = time.time()

        # Add 6 requests (over limit of 5)
        for i in range(6):
            tracker.record_request(now - i)

        assert tracker.can_make_request(now) is False

    def test_expired_requests_removed(self):
        """Test that expired requests are removed from tracker."""
        tracker = RateLimitTracker(requests=5, window=60)
        now = time.time()

        # Add requests that should be expired
        for i in range(3):
            tracker.record_request(now - 70)  # 70 seconds ago, should be expired

        # Add recent requests
        for i in range(2):
            tracker.record_request(now - i)

        # Should be able to make request (only 2 recent requests)
        assert tracker.can_make_request(now) is True
        assert len(tracker.timestamps) == 2

    def test_get_wait_time(self):
        """Test getting wait time."""
        tracker = RateLimitTracker(requests=2, window=60)
        now = time.time()

        # No wait when under limit
        assert tracker.get_wait_time(now) == 0

        # Add requests to hit limit
        tracker.record_request(now - 10)  # 10 seconds ago
        tracker.record_request(now - 5)  # 5 seconds ago

        # Should wait until oldest request expires
        wait_time = tracker.get_wait_time(now)
        assert 50 <= wait_time <= 55  # Should be ~55 seconds (60-5)

    def test_get_current_usage(self):
        """Test getting current usage."""
        tracker = RateLimitTracker(requests=10, window=60)
        now = time.time()

        # Add some requests
        for i in range(5):
            tracker.record_request(now - i)

        assert tracker.get_current_usage(now) == 5

        # Add expired request
        tracker.record_request(now - 70)
        assert tracker.get_current_usage(now) == 5  # Expired request not counted


class TestCircuitBreaker:
    """Test cases for CircuitBreaker."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test circuit breaker initialization."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout == 60
        assert breaker.failure_count == 0
        assert breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_closed_allows_requests(self):
        """Test that closed circuit allows requests."""
        breaker = CircuitBreaker()
        assert await breaker.before_request() is True

    @pytest.mark.asyncio
    async def test_success_keeps_closed(self):
        """Test that success keeps circuit closed."""
        breaker = CircuitBreaker()
        await breaker.on_success()
        assert breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_failures_open_circuit(self):
        """Test that failures open circuit after threshold."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        # Record failures
        for i in range(3):
            await breaker.on_failure()

        assert breaker.state == "open"
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_open_blocks_requests(self):
        """Test that open circuit blocks requests."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60)

        # Open circuit
        await breaker.on_failure()
        await breaker.on_failure()

        assert breaker.state == "open"
        assert await breaker.before_request() is False

    @pytest.mark.asyncio
    async def test_recovery_timeout_half_open(self):
        """Test that recovery timeout transitions to half-open."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        # Open circuit
        await breaker.on_failure()
        await breaker.on_failure()

        assert breaker.state == "open"

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Should now be half-open
        assert await breaker.before_request() is True
        assert breaker.state == "half-open"
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_success_closes(self):
        """Test that success in half-open closes circuit."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        # Open circuit
        await breaker.on_failure()
        await breaker.on_failure()

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Make request (transitions to half-open)
        await breaker.before_request()

        # Record success
        await breaker.on_success()

        assert breaker.state == "closed"
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self):
        """Test that failure in half-open reopens circuit."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        # Open circuit
        await breaker.on_failure()
        await breaker.on_failure()

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Make request (transitions to half-open)
        await breaker.before_request()

        # Record failure
        await breaker.on_failure()

        assert breaker.state == "open"
        assert breaker.failure_count == 1


class TestRateLimiter:
    """Test cases for RateLimiter."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter()
        assert len(limiter.app_limiters) > 0
        assert len(limiter.method_limiters) == 0
        assert len(limiter.circuit_breakers) > 0
        assert limiter.max_retries == 3

    @pytest.mark.asyncio
    async def test_wait_if_needed_no_limit(self):
        """Test wait_if_needed when no limits are exceeded."""
        limiter = RateLimiter()
        # Should not raise or wait
        await limiter.wait_if_needed("test/endpoint")

    @pytest.mark.asyncio
    async def test_update_limits(self):
        """Test updating limits from headers."""
        limiter = RateLimiter()
        headers = {
            "X-App-Rate-Limit": "20:1,100:120",
            "X-App-Rate-Count": "15:1,80:120",
            "X-Method-Rate-Limit": "50:60",
            "X-Method-Rate-Count": "25:60",
        }

        limiter.update_limits(headers, "test/endpoint")

        # Should have created method limiters
        assert len(limiter.method_limiters) > 0

    @pytest.mark.asyncio
    async def test_handle_429(self):
        """Test handling 429 response."""
        limiter = RateLimiter()
        headers = {"Retry-After": "5"}

        wait_time = await limiter.handle_429(headers, "test/endpoint")
        assert wait_time == 5.0

    @pytest.mark.asyncio
    async def test_handle_429_no_retry_after(self):
        """Test handling 429 response without Retry-After."""
        limiter = RateLimiter()
        headers = {}

        wait_time = await limiter.handle_429(headers, "test/endpoint")
        assert wait_time == 1.0

    @pytest.mark.asyncio
    async def test_calculate_backoff(self):
        """Test exponential backoff calculation."""
        limiter = RateLimiter()

        # Test different attempts
        backoff1 = await limiter.calculate_backoff(0)
        backoff2 = await limiter.calculate_backoff(1)
        backoff3 = await limiter.calculate_backoff(2)

        assert backoff2 > backoff1  # Should increase exponentially
        assert backoff3 > backoff2

        # Test max backoff
        backoff_large = await limiter.calculate_backoff(10)
        assert backoff_large <= limiter.max_backoff

    @pytest.mark.asyncio
    async def test_record_success(self):
        """Test recording successful request."""
        limiter = RateLimiter()
        await limiter.record_success("test/endpoint")

        # Should reset circuit breakers
        for breaker in limiter.circuit_breakers.values():
            assert breaker.state == "closed"
            assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_record_failure(self):
        """Test recording failed request."""
        limiter = RateLimiter()
        await limiter.record_failure("test/endpoint", status_code=429)

        # Should trigger 429 circuit breaker
        assert limiter.circuit_breakers["429"].failure_count == 1

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting rate limiter statistics."""
        limiter = RateLimiter()
        stats = limiter.get_stats()

        assert "app_limits" in stats
        assert "method_limits" in stats
        assert "circuit_breakers" in stats
        assert "last_requests" in stats

        # Should have app limit stats
        assert len(stats["app_limits"]) > 0

    @pytest.mark.asyncio
    async def test_reset(self):
        """Test resetting rate limiter."""
        limiter = RateLimiter()

        # Add some state
        await limiter.record_failure("test/endpoint")
        limiter.last_request_time["test"] = time.time()

        # Reset
        await limiter.reset()

        # Should clear most state
        assert len(limiter.method_limiters) == 0
        assert len(limiter.last_request_time) == 0

        # Should reinitialize app limits
        assert len(limiter.app_limiters) > 0

        # Should reset circuit breakers
        for breaker in limiter.circuit_breakers.values():
            assert breaker.state == "closed"
            assert breaker.failure_count == 0

    def test_get_endpoint_key(self):
        """Test endpoint key generation."""
        limiter = RateLimiter()

        key1 = limiter._get_endpoint_key(
            "https://europe.api.riotgames.com/lol/match/v5/matches", "GET"
        )
        key2 = limiter._get_endpoint_key(
            "https://europe.api.riotgames.com/lol/summoner/v4/summoners", "POST"
        )

        assert key1 == "GET:lol-match-v5-matches"
        assert key2 == "POST:lol-summoner-v4-summoners"
        assert key1 != key2

    @pytest.mark.asyncio
    async def test_request_spacing(self):
        """Test request spacing enforcement."""
        limiter = RateLimiter()
        limiter.request_spacing = 0.1  # 100ms spacing

        # First request should not wait
        start_time = time.time()
        await limiter.wait_if_needed("test/endpoint", "GET")
        elapsed = time.time() - start_time
        assert elapsed < 0.05  # Should be very fast

        # Second request should wait
        start_time = time.time()
        await limiter.wait_if_needed("test/endpoint", "GET")
        elapsed = time.time() - start_time
        assert elapsed >= 0.09  # Should wait at least 90ms

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test concurrent request handling."""
        limiter = RateLimiter()
        limiter.request_spacing = 0.05  # 50ms spacing

        # Make concurrent requests
        tasks = []
        for i in range(3):
            task = limiter.wait_if_needed(f"test/endpoint/{i}", "GET")
            tasks.append(task)

        # Should all complete without errors
        await asyncio.gather(*tasks)

        # Check that requests were spaced out
        assert len(limiter.last_request_time) == 3
