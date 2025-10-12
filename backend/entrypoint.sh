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

# Initialize database tables
echo "============================================"
echo "Initializing database tables..."
echo "============================================"
uv run python -m app.init_db init

# Check initialization exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "============================================"
    echo "Database initialization completed successfully!"
    echo "============================================"
    echo ""
else
    echo ""
    echo "============================================"
    echo "ERROR: Database initialization failed!"
    echo "============================================"
    exit 1
fi

# Start the application
echo "Starting application..."
echo ""
exec "$@"
