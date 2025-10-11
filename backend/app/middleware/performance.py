"""Performance monitoring middleware for API response tracking and metrics collection."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Any
import time
import threading
import structlog
from starlette.middleware.base import RequestResponseEndpoint

logger = structlog.get_logger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring API performance and collecting metrics."""

    def __init__(self, app: ASGIApp):
        """
        Initialize performance middleware.

        Args:
            app: ASGI application
        """
        super().__init__(app)
        self.slow_request_threshold: float = 2.0  # seconds
        self.db_query_threshold: float = 0.5  # seconds

        # Thread-safe metrics storage
        self._lock: threading.Lock = threading.Lock()

        # Performance metrics
        self.request_metrics: RequestMetricsCollector = RequestMetricsCollector()
        self.db_monitor: DatabaseQueryMonitor = DatabaseQueryMonitor()
        self.cache_metrics: CacheMetricsCollector = CacheMetricsCollector()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process incoming request with performance monitoring.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint handler

        Returns:
            HTTP response
        """
        start_time = time.time()
        request_id = f"req_{int(time.time() * 1000)}"

        # Add request ID to logger context
        logger.bind(request_id=request_id, method=request.method, url=str(request.url))

        try:
            # Process the request
            response = await call_next(request)

            # Calculate timing
            duration = time.time() - start_time

            # Record metrics
            self.request_metrics.record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration=duration,
            )

            # Log performance metrics
            logger.info(
                "Request completed",
                status_code=response.status_code,
                duration_seconds=round(duration, 3),
                duration_ms=round(duration * 1000),
                request_id=request_id,
            )

            # Log slow requests
            if duration > self.slow_request_threshold:
                logger.warning(
                    "Slow request detected",
                    duration_seconds=round(duration, 3),
                    threshold=self.slow_request_threshold,
                    endpoint=request.url.path,
                    request_id=request_id,
                )

            # Add performance headers
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Request failed",
                duration_seconds=round(duration, 3),
                error=str(e),
                request_id=request_id,
            )
            raise

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get comprehensive performance metrics."""
        with self._lock:
            return {
                "request_metrics": self.request_metrics.get_metrics(),
                "db_metrics": self.db_monitor.get_stats(),
                "cache_metrics": self.cache_metrics.get_metrics(),
                "thresholds": {
                    "slow_request_threshold": self.slow_request_threshold,
                    "db_query_threshold": self.db_query_threshold,
                },
            }

    def log_database_query(
        self, query: str, duration: float, params: dict[str, Any] | None = None
    ) -> None:
        """Log a database query with performance metrics."""
        self.db_monitor.log_query(query, duration, params)

    def record_cache_operation(
        self, operation: str, cache_type: str, hit: bool, duration: float
    ):
        """Record cache operation metrics."""
        self.cache_metrics.record_operation(operation, cache_type, hit, duration)

    def reset_metrics(self) -> None:
        """Reset all performance metrics."""
        self.request_metrics.reset()
        self.db_monitor.reset()
        self.cache_metrics.reset()
        logger.info("Performance metrics reset")


class RequestMetricsCollector:
    """Collect and analyze API request metrics."""

    def __init__(self):
        """Initialize request metrics collector."""
        self.endpoint_stats: dict[str, dict[str, Any]] = {}
        self.error_rates: dict[str, dict[str, int]] = {}
        self.total_requests: int = 0
        self.total_duration: float = 0.0
        self._lock: threading.Lock = threading.Lock()

    def record_request(
        self, endpoint: str, method: str, status_code: int, duration: float
    ) -> None:
        """Record a request for metrics collection."""
        with self._lock:
            self.total_requests += 1
            self.total_duration += duration

            key = f"{method}:{endpoint}"

            # Initialize endpoint stats if not exists
            if key not in self.endpoint_stats:
                self.endpoint_stats[key] = {
                    "count": 0,
                    "total_duration": 0.0,
                    "avg_duration": 0.0,
                    "min_duration": float("inf"),
                    "max_duration": 0.0,
                    "p95_duration": 0.0,
                    "durations": [],
                }

            stats = self.endpoint_stats[key]
            stats["count"] += 1
            stats["total_duration"] += duration
            stats["avg_duration"] = stats["total_duration"] / stats["count"]
            stats["min_duration"] = min(stats["min_duration"], duration)
            stats["max_duration"] = max(stats["max_duration"], duration)

            # Keep last 100 durations for percentile calculation
            stats["durations"].append(duration)
            if len(stats["durations"]) > 100:
                stats["durations"].pop(0)

            # Calculate p95
            if stats["durations"]:
                sorted_durations = sorted(stats["durations"])
                stats["p95_duration"] = sorted_durations[
                    int(len(sorted_durations) * 0.95)
                ]

            # Track error rates
            if status_code >= 400:
                if key not in self.error_rates:
                    self.error_rates[key] = {"errors": 0, "total": 0}
                self.error_rates[key]["errors"] += 1
                self.error_rates[key]["total"] += 1
            else:
                if key not in self.error_rates:
                    self.error_rates[key] = {"errors": 0, "total": 0}
                self.error_rates[key]["total"] += 1

    def get_metrics(self) -> dict[str, Any]:
        """Get current request metrics."""
        with self._lock:
            avg_response_time = (
                self.total_duration / self.total_requests
                if self.total_requests > 0
                else 0
            )

            return {
                "total_requests": self.total_requests,
                "total_duration": round(self.total_duration, 3),
                "avg_response_time": round(avg_response_time, 3),
                "requests_per_second": self._calculate_rps(),
                "endpoint_stats": self.endpoint_stats,
                "error_rates": {
                    endpoint: {
                        "error_rate": (
                            (stats["errors"] / stats["total"]) * 100
                            if stats["total"] > 0
                            else 0
                        ),
                        "errors": stats["errors"],
                        "total": stats["total"],
                    }
                    for endpoint, stats in self.error_rates.items()
                },
                "slow_endpoints": self._get_slow_endpoints(),
            }

    def _calculate_rps(self) -> float:
        """Calculate requests per second (simplified)."""
        # This is a simplified version - in production you'd track timestamps
        if self.total_requests == 0:
            return 0.0
        # Assume metrics are collected over the last minute
        return min(self.total_requests / 60.0, 1000.0)  # Cap at 1000 RPS

    def _get_slow_endpoints(self) -> list[dict[str, Any]]:
        """Get list of slow endpoints sorted by average duration."""
        slow_endpoints: list[dict[str, Any]] = []
        for endpoint, stats in self.endpoint_stats.items():
            if stats["avg_duration"] > 1.0:  # Slower than 1 second
                slow_endpoints.append(
                    {
                        "endpoint": endpoint,
                        "avg_duration": round(stats["avg_duration"], 3),
                        "count": stats["count"],
                        "p95_duration": round(stats["p95_duration"], 3),
                    }
                )

        return sorted(slow_endpoints, key=lambda x: x["avg_duration"], reverse=True)[
            :10
        ]

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self.endpoint_stats.clear()
            self.error_rates.clear()
            self.total_requests = 0
            self.total_duration = 0.0


class DatabaseQueryMonitor:
    """Monitor database query performance."""

    def __init__(self):
        """Initialize database query monitor."""
        self.slow_queries: list[dict[str, Any]] = []
        self.query_stats: dict[str, float | int] = {
            "total": 0,
            "slow": 0,
            "avg_duration": 0.0,
            "total_duration": 0.0,
        }
        self._lock: threading.Lock = threading.Lock()

    def log_query(
        self, query: str, duration: float, params: dict[str, Any] | None = None
    ) -> None:
        """Log a database query with performance metrics."""
        with self._lock:
            self.query_stats["total"] += 1
            self.query_stats["total_duration"] += duration
            self.query_stats["avg_duration"] = (
                self.query_stats["total_duration"] / self.query_stats["total"]
            )

            if duration > 0.5:  # Slow query threshold
                self.query_stats["slow"] += 1
                self.slow_queries.append(
                    {
                        "query": query[:200],  # Truncate long queries
                        "duration": round(duration, 3),
                        "timestamp": time.time(),
                        "params": params,
                    }
                )

                # Keep only last 50 slow queries
                if len(self.slow_queries) > 50:
                    self.slow_queries = self.slow_queries[-50:]

                logger.warning(
                    "Slow database query",
                    query_duration=round(duration, 3),
                    query=query[:100],
                )

    def get_stats(self) -> dict[str, Any]:
        """Get database query performance statistics."""
        with self._lock:
            result: dict[str, Any] = {
                "query_stats": self.query_stats.copy(),
                "recent_slow_queries": [
                    {
                        "query": q["query"],
                        "duration": q["duration"],
                        "timestamp": q["timestamp"],
                    }
                    for q in self.slow_queries[-10:]  # Last 10 slow queries
                ],
                "slow_query_rate": (
                    (self.query_stats["slow"] / self.query_stats["total"]) * 100
                    if self.query_stats["total"] > 0
                    else 0
                ),
            }
            return result

    def reset(self) -> None:
        """Reset all query statistics."""
        with self._lock:
            self.slow_queries.clear()
            self.query_stats = {
                "total": 0,
                "slow": 0,
                "avg_duration": 0.0,
                "total_duration": 0.0,
            }


class CacheMetricsCollector:
    """Collect cache performance metrics."""

    def __init__(self):
        """Initialize cache metrics collector."""
        self.operations: dict[str, dict[str, dict[str, float | int]]] = {
            "get": {
                "local": {"hits": 0, "misses": 0, "total_time": 0.0},
                "redis": {"hits": 0, "misses": 0, "total_time": 0.0},
            },
            "set": {
                "local": {"count": 0, "total_time": 0.0},
                "redis": {"count": 0, "total_time": 0.0},
            },
            "delete": {
                "local": {"count": 0, "total_time": 0.0},
                "redis": {"count": 0, "total_time": 0.0},
            },
        }
        self._lock: threading.Lock = threading.Lock()

    def record_operation(
        self,
        operation: str,
        cache_type: str,
        hit: bool | None = None,
        duration: float = 0.0,
    ) -> None:
        """Record a cache operation."""
        with self._lock:
            if operation == "get" and hit is not None:
                if hit:
                    self.operations[operation][cache_type]["hits"] += 1
                else:
                    self.operations[operation][cache_type]["misses"] += 1
                self.operations[operation][cache_type]["total_time"] += duration
            else:
                self.operations[operation][cache_type]["count"] += 1
                self.operations[operation][cache_type]["total_time"] += duration

    def get_metrics(self) -> dict[str, Any]:
        """Get cache performance metrics."""
        with self._lock:
            metrics: dict[str, Any] = {}
            for operation, cache_types in self.operations.items():
                metrics[operation] = {}
                for cache_type, stats in cache_types.items():
                    metrics[operation][cache_type] = {
                        **stats,
                        "avg_time": stats["total_time"]
                        / max(
                            stats.get(
                                "count", stats.get("hits", 0) + stats.get("misses", 0)
                            ),
                            1,
                        ),
                    }

                    # Calculate hit rate for get operations
                    if operation == "get":
                        total = stats["hits"] + stats["misses"]
                        metrics[operation][cache_type]["hit_rate"] = (
                            (stats["hits"] / total) * 100 if total > 0 else 0
                        )

            return metrics

    def reset(self):
        """Reset all cache metrics."""
        with self._lock:
            # Reinitialize operations dict to reset all values
            self.operations = {
                "get": {
                    "local": {"hits": 0, "misses": 0, "total_time": 0.0},
                    "redis": {"hits": 0, "misses": 0, "total_time": 0.0},
                },
                "set": {
                    "local": {"count": 0, "total_time": 0.0},
                    "redis": {"count": 0, "total_time": 0.0},
                },
                "delete": {
                    "local": {"count": 0, "total_time": 0.0},
                    "redis": {"count": 0, "total_time": 0.0},
                },
            }
