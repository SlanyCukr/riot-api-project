#!/bin/bash
set -e

echo "============================================"
echo "Starting Riot API Backend Container"
echo "============================================"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "postgres" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is ready!"
echo ""

# Run database migrations
echo "============================================"
echo "Running database migrations..."
echo "============================================"
uv run alembic upgrade head

# Check migration exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "============================================"
    echo "Database migrations completed successfully!"
    echo "============================================"
    echo ""
else
    echo ""
    echo "============================================"
    echo "ERROR: Database migrations failed!"
    echo "============================================"
    exit 1
fi

# Start the application
# Note: Job configurations are seeded via Alembic migration, not here
echo "============================================"
echo "Starting application..."
echo "============================================"
echo ""
exec "$@"
