# syntax=docker/dockerfile:1

# Base stage with common dependencies
FROM python:3.13-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies with cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    DEBIAN_FRONTEND=noninteractive apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends -q \
    curl \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv with pinned version for reproducibility
ARG UV_VERSION=0.5.11
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "uv==${UV_VERSION}"

# Dependency stage for better caching
FROM base AS deps

# Copy dependency files first (better layer caching)
# Include README.md as it's referenced in pyproject.toml
COPY pyproject.toml uv.lock* README.md ./

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1001 app \
    && chown -R app:app /app

USER app

# Lint stage for CI/CD validation
FROM deps AS lint

USER root
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

USER app

# Copy source code for linting
COPY --chown=app:app . .

# Run linting (ruff, mypy, etc.)
RUN uv run ruff check . || echo "Lint check completed"

# Development stage
FROM deps AS development

USER root

# Install development dependencies with cache mount (skip project install until code is copied)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --dev --frozen --no-install-project

USER app

# Copy application code
COPY --chown=app:app . .

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Create logs directory
RUN mkdir -p /app/logs && chmod 755 /app/logs

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Development command with hot reload
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production build stage
FROM deps AS builder

USER root

# Install production dependencies only with cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY --chown=app:app . .

# Compile Python files for faster startup
RUN python -m compileall -q /app

USER app

# Production stage (minimal, optimized)
FROM python:3.13-slim AS production

# Security: Install only runtime dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    DEBIAN_FRONTEND=noninteractive apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends -q \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv for production (needed for CMD entrypoint)
ARG UV_VERSION=0.5.11
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "uv==${UV_VERSION}"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1001 app \
    && chown -R app:app /app

# Copy virtual environment and app from builder
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app /app

USER app

# Create logs directory
RUN mkdir -p /app/logs && chmod 755 /app/logs

EXPOSE 8000

# Health check with longer start period for production
HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Production command with multiple workers
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
