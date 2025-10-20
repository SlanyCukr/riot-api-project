"""Main FastAPI application for the Riot API Backend."""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_global_settings, get_riot_api_key
from app.api.players import router as players_router
from app.api.matches import router as matches_router
from app.api.detection import router as detection_router
from app.api.jobs import router as jobs_router
from app.api.settings import router as settings_router
from app.api.matchmaking import router as matchmaking_router
from app.jobs import start_scheduler, shutdown_scheduler
from app.jobs.log_capture import job_log_capture
import structlog
from structlog import contextvars as structlog_contextvars


# Configure logging
settings = get_global_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = structlog.get_logger(__name__)

# Configure rate limiter
limiter = Limiter(key_func=get_remote_address)

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog_contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        job_log_capture,  # Capture logs after all context is added
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    context_class=dict,
    cache_logger_on_first_use=True,
)


async def _validate_api_key_configuration() -> None:
    """Validate and log Riot API key configuration status."""
    try:
        api_key = await get_riot_api_key()
        if not api_key or api_key == "your_riot_api_key_here":
            logger.warning(
                "⚠️  RIOT_API_KEY not configured! Set it in .env file or update via /settings.",
                hint="Get your key from https://developer.riotgames.com",
            )
        elif api_key.startswith("RGAPI-"):
            logger.info("✓ Riot API key configured (development key detected)")
            logger.warning(
                "⚠️  Development API keys expire every 24 hours!",
                hint="Update via web UI at /settings or with ./scripts/update-riot-api-key.sh",
            )
        else:
            logger.info("✓ Riot API key configured")
    except Exception as e:
        logger.warning("Could not validate API key configuration", error=str(e))


async def _start_scheduler_safely() -> None:
    """Start job scheduler with error handling."""
    try:
        scheduler = await start_scheduler()
        if scheduler:
            logger.info("Job scheduler started")
    except Exception as e:
        logger.error(
            "Failed to start job scheduler",
            error=str(e),
            error_type=type(e).__name__,
        )
        # Don't fail startup if scheduler fails - allows manual operations


async def _shutdown_scheduler_safely() -> None:
    """Shutdown job scheduler with error handling."""
    try:
        await shutdown_scheduler()
        logger.info("Job scheduler shut down")
    except Exception as e:
        logger.error(
            "Error during scheduler shutdown",
            error=str(e),
            error_type=type(e).__name__,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting up Riot API Backend application")
    await _validate_api_key_configuration()
    await _start_scheduler_safely()
    yield
    logger.info("Shutting down Riot API Backend application")
    await _shutdown_scheduler_safely()


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
        "name": "player-analysis",
        "description": "Player analysis algorithms and analysis endpoints.",
    },
    {
        "name": "jobs",
        "description": "Job management and monitoring endpoints for automated tasks.",
    },
    {
        "name": "settings",
        "description": "System settings and configuration management.",
    },
    {
        "name": "matchmaking-analysis",
        "description": "Matchmaking analysis endpoints for analyzing team fairness.",
    },
    {
        "name": "health",
        "description": "Health check and system status endpoints.",
    },
]

# Create FastAPI application
app = FastAPI(
    title="Riot API - Player Analysis Service",
    description="""
    A comprehensive League of Legends player analysis API.

    ## Features

    * **Player Search**: Search players by Riot ID or summoner name
    * **Match History**: Retrieve and analyze match history
    * **Player Analysis**: Analyze players using multiple algorithms
    * **Statistics**: Player performance statistics and analysis

    ## Authentication

    Currently, this API does not require authentication. This will change in production.

    ## Rate Limiting

    Requests are rate-limited based on Riot API constraints. Database serves as the primary cache.
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

# Configure rate limiter for FastAPI app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(players_router, prefix="/api/v1", tags=["players"])
app.include_router(matches_router, prefix="/api/v1", tags=["matches"])
app.include_router(detection_router, prefix="/api/v1", tags=["player-analysis"])
app.include_router(jobs_router, prefix="/api/v1", tags=["jobs"])
app.include_router(settings_router, prefix="/api/v1", tags=["settings"])
app.include_router(matchmaking_router, prefix="/api/v1", tags=["matchmaking-analysis"])

# Legacy route compatibility (tests and existing clients expect root-level paths)
app.include_router(players_router)
app.include_router(matches_router)
app.include_router(detection_router)
app.include_router(jobs_router)


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
