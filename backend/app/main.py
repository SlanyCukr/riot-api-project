"""
Main FastAPI application for the Riot API Backend
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.players import router as players_router
from app.api.matches import router as matches_router
from app.api.detection import router as detection_router
from app.middleware.performance import PerformanceMiddleware
import structlog


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    context_class=dict,
    cache_logger_on_first_use=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting up Riot API Backend application")

    yield

    logger.info("Shutting down Riot API Backend application")


# Create FastAPI application
app = FastAPI(
    title="Riot API Backend",
    description="Backend service for Riot API match history and smurf detection",
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.debug
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure performance monitoring middleware
app.add_middleware(PerformanceMiddleware)

# Include API routers
app.include_router(players_router, prefix="/api/v1")
app.include_router(matches_router, prefix="/api/v1")
app.include_router(detection_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Riot API Backend is running", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Application is running",
        "version": "0.1.0",
        "debug": settings.debug
    }


@app.get("/api/v1/health")
async def api_health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "service": "riot-api-backend",
        "version": "0.1.0"
    }




if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )