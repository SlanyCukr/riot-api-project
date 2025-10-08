#!/bin/bash

# Clean local development artifacts for Docker-only development
# This script removes local dependencies and build artifacts that should
# only exist inside Docker containers

set -e

echo "🧹 Cleaning local development artifacts..."

# Remove Python virtual environments
echo "Removing Python virtual environments..."
find . -name ".venv" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "venv" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove Node.js dependencies
echo "Removing Node.js dependencies..."
find . -name "node_modules" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove build artifacts
echo "Removing build artifacts..."
find . -name "dist" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "build" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove cache files
echo "Removing cache files..."
find . -name ".cache" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name ".mypy_cache" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove log files
echo "Removing log files..."
find . -name "*.log" -type f -delete 2>/dev/null || true
find . -name "logs" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove temporary files
echo "Removing temporary files..."
find . -name "*.tmp" -type f -delete 2>/dev/null || true
find . -name "*.temp" -type f -delete 2>/dev/null || true
find . -name ".eslintcache" -type f -delete 2>/dev/null || true

echo "✅ Cleanup complete! Your project is now ready for Docker-only development."
echo "💡 Run 'docker-compose up --build' to start the application."
