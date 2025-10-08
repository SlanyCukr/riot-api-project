FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Copy dependency files
COPY --chown=app:app pyproject.toml ./
COPY --chown=app:app README.md ./

# Development stage
FROM base AS development

# Install development dependencies
RUN uv sync --dev

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

# Development command
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base AS production

# Install production dependencies
RUN uv sync --frozen

# Copy application code
COPY --chown=app:app . .

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Create logs directory
RUN mkdir -p /app/logs && chmod 755 /app/logs

# Create .venv directory if it doesn't exist
RUN if [ ! -d ".venv" ]; then uv sync --frozen; fi

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Production command
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
