"""Main FastAPI application for the Riot API Backend."""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_global_settings
from app.api.players import router as players_router
from app.api.matches import router as matches_router
from app.api.detection import router as detection_router
from app.api.dependencies import RiotDataManagerDep
from app.middleware.performance import PerformanceMiddleware
from app.riot_api.cache import RiotAPICache
import structlog


# Configure logging
settings = get_global_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = structlog.get_logger(__name__)

# Configure structlog for better performance logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    context_class=dict,
    cache_logger_on_first_use=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting up Riot API Backend application")

    yield

    logger.info("Shutting down Riot API Backend application")


# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "players",
        "description": "Operations for searching and managing player data.",
    },
    {
        "name": "matches",
        "description": "Operations for retrieving and analyzing match history.",
    },
    {
        "name": "smurf-detection",
        "description": "Smurf detection algorithms and analysis endpoints.",
    },
    {
        "name": "health",
        "description": "Health check and system status endpoints.",
    },
]

# Create FastAPI application
app = FastAPI(
    title="Riot API - Smurf Detection Service",
    description="""
    A comprehensive League of Legends player analysis and smurf detection API.

    ## Features

    * **Player Search**: Search players by Riot ID or summoner name
    * **Match History**: Retrieve and analyze match history
    * **Smurf Detection**: Identify potential smurf accounts using multiple algorithms
    * **Statistics**: Player performance statistics and analysis

    ## Authentication

    Currently, this API does not require authentication. This will change in production.

    ## Rate Limiting

    Requests are rate-limited based on Riot API constraints. Cache is used extensively to reduce API calls.
    """,
    version="0.1.0",
    contact={
        "name": "Riot API Project",
        "url": "https://github.com/yourusername/riot-api-project",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    debug=settings.debug,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure performance monitoring middleware
app.add_middleware(PerformanceMiddleware)

# Include API routers
app.include_router(players_router, prefix="/api/v1", tags=["players"])
app.include_router(matches_router, prefix="/api/v1", tags=["matches"])
app.include_router(detection_router, prefix="/api/v1", tags=["smurf-detection"])


@app.get("/", tags=["health"])
async def root():
    """
    Root endpoint - API welcome message.

    Returns basic information about the API and its version.
    """
    return {"message": "Riot API Backend is running", "version": "0.1.0"}


@app.get("/health", tags=["health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns the health status of the application including:
    - Overall health status
    - Application version
    - Debug mode status

    This endpoint can be used by monitoring tools and load balancers
    to check if the service is running correctly.
    """
    return {
        "status": "healthy",
        "message": "Application is running",
        "version": "0.1.0",
        "debug": settings.debug,
    }


@app.get("/api/v1/health", tags=["health"])
async def api_health_check() -> Dict[str, str]:
    """
    Check API v1 health status.

    Returns health status specifically for the v1 API endpoints.
    This is the recommended health check endpoint for production use.

    ## Response
    - **status**: Health status (healthy/unhealthy)
    - **service**: Service identifier
    - **version**: API version
    """
    return {"status": "healthy", "service": "riot-api-backend", "version": "0.1.0"}


@app.get("/api/v1/health/cache-stats", tags=["health"])
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics for monitoring and debugging.

    Returns hit rates, sizes, and performance metrics for all cache instances.

    ## Response
    Returns statistics for each cache type:
    - **size**: Current number of cached entries
    - **maxsize**: Maximum cache capacity
    - **hits**: Number of cache hits
    - **misses**: Number of cache misses
    - **hit_rate**: Cache hit rate (0.0 to 1.0)

    ## Cache Types
    - **account_cache**: Player account data (24h TTL)
    - **summoner_cache**: Summoner information (24h TTL)
    - **match_cache**: Match details (7 days TTL)
    - **match_list_cache**: Match lists (5 min TTL)
    - **league_cache**: League/rank data (1h TTL)
    - **active_game_cache**: Live game data (1 min TTL)
    - **featured_games_cache**: Featured games (2 min TTL)
    - **shard_cache**: Shard information (1h TTL)

    This endpoint is useful for:
    - Monitoring cache performance
    - Debugging caching issues
    - Capacity planning
    """
    return RiotAPICache.get_stats()


@app.get("/api/v1/health/rate-limit-status", tags=["health"])
async def get_rate_limit_status(
    riot_data_manager: RiotDataManagerDep,
) -> Dict[str, Any]:
    """
    Get current rate limit status for monitoring and user feedback.

    Returns information about rate limits, cooldown periods, and API usage.

    ## Response
    Returns rate limit information including:
    - **can_fetch**: Whether API calls can be made
    - **reason**: Reason if calls cannot be made
    - **wait_time**: Time to wait before next API call (seconds)
    - **priority_level**: Current priority level for requests
    - **api_stats**: Detailed API usage statistics
    - **circuit_breakers**: Circuit breaker status

    This endpoint is useful for:
    - Monitoring rate limit usage
    - Implementing user-facing cooldown UI
    - Debugging rate limit issues
    """
    try:
        status = await riot_data_manager.get_rate_limit_status()
        return {
            "status": "success",
            "data": status,
            "message": "Rate limit status retrieved successfully",
        }
    except Exception as e:
        logger.error("Failed to get rate limit status", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to retrieve rate limit status",
        }


@app.get("/api/v1/health/data-stats", tags=["health"])
async def get_data_stats(riot_data_manager: RiotDataManagerDep) -> Dict[str, Any]:
    """
    Get comprehensive data management statistics.

    Returns tracking stats, queue status, and usage patterns.

    ## Response
    Returns comprehensive statistics including:
    - **tracking_stats**: Data freshness and hit rates by type
    - **pending_requests**: Number of queued API requests
    - **recent_rate_limits**: Recent rate limit events
    - **rate_limit_status**: Current rate limit status

    This endpoint is useful for:
    - Monitoring data freshness
    - Analyzing cache hit rates
    - Understanding usage patterns
    - Debugging data management issues
    """
    try:
        stats = await riot_data_manager.get_data_stats()
        return {
            "status": "success",
            "data": stats,
            "message": "Data statistics retrieved successfully",
        }
    except Exception as e:
        logger.error("Failed to get data stats", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to retrieve data statistics",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
