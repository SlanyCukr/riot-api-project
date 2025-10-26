#!/bin/bash
# Setup PostgreSQL Logical Replication for DEV Environment
# This script creates a subscription to the production database

set -e

echo "PostgreSQL Logical Replication Setup for DEV"
echo "=============================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create .env file with REPLICATION_* variables"
    exit 1
fi

# Load environment variables from .env
set -a
source .env
set +a

# Check required variables
if [ -z "$REPLICATION_PROD_HOST" ] || [ -z "$REPLICATION_PROD_PORT" ] || \
   [ -z "$REPLICATION_PROD_USER" ] || [ -z "$REPLICATION_PROD_PASSWORD" ] || \
   [ -z "$REPLICATION_PROD_DB" ]; then
    echo "Error: Missing required REPLICATION_* environment variables in .env"
    echo ""
    echo "Required variables:"
    echo "  REPLICATION_PROD_HOST=<production_host>"
    echo "  REPLICATION_PROD_PORT=<production_port>"
    echo "  REPLICATION_PROD_USER=<production_user>"
    echo "  REPLICATION_PROD_PASSWORD=<production_password>"
    echo "  REPLICATION_PROD_DB=<production_database>"
    echo "  REPLICATION_PUBLICATION_NAME=<publication_name>"
    echo "  REPLICATION_SUBSCRIPTION_NAME=<subscription_name>"
    exit 1
fi

# Use defaults if not specified
PUBLICATION_NAME="${REPLICATION_PUBLICATION_NAME:-prod_to_dev_pub}"
SUBSCRIPTION_NAME="${REPLICATION_SUBSCRIPTION_NAME:-dev_from_prod_sub}"

echo "Configuration:"
echo "  Production Host: $REPLICATION_PROD_HOST"
echo "  Production Port: $REPLICATION_PROD_PORT"
echo "  Production Database: $REPLICATION_PROD_DB"
echo "  Production User: $REPLICATION_PROD_USER"
echo "  Publication Name: $PUBLICATION_NAME"
echo "  Subscription Name: $SUBSCRIPTION_NAME"
echo ""

# Test connection to production
echo "Testing connection to production..."
if ! docker run --rm postgres:18-alpine psql \
    "host=$REPLICATION_PROD_HOST port=$REPLICATION_PROD_PORT dbname=$REPLICATION_PROD_DB user=$REPLICATION_PROD_USER password=$REPLICATION_PROD_PASSWORD" \
    -c "SELECT version();" > /dev/null 2>&1; then
    echo "Error: Cannot connect to production database"
    echo "Please check your REPLICATION_* credentials in .env"
    exit 1
fi
echo "✓ Connection successful"
echo ""

# Check if local PostgreSQL is running
echo "Checking local PostgreSQL..."
if ! docker compose ps postgres | grep -q "Up"; then
    echo "Error: Local PostgreSQL is not running"
    echo "Please start it with: docker compose up -d postgres"
    exit 1
fi
echo "✓ Local PostgreSQL is running"
echo ""

# Check if subscription already exists
echo "Checking if subscription already exists..."
if docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -tAc "SELECT 1 FROM pg_subscription WHERE subname = '$SUBSCRIPTION_NAME';" | grep -q 1; then
    echo "⚠ Subscription '$SUBSCRIPTION_NAME' already exists"
    read -p "Do you want to drop and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Dropping existing subscription..."
        docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
            -c "DROP SUBSCRIPTION $SUBSCRIPTION_NAME;"
        echo "✓ Subscription dropped"
    else
        echo "Aborted. Keeping existing subscription."
        exit 0
    fi
fi
echo ""

# Create subscription
echo "Creating subscription '$SUBSCRIPTION_NAME'..."
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<EOF
CREATE SUBSCRIPTION $SUBSCRIPTION_NAME
    CONNECTION 'host=$REPLICATION_PROD_HOST port=$REPLICATION_PROD_PORT dbname=$REPLICATION_PROD_DB user=$REPLICATION_PROD_USER password=$REPLICATION_PROD_PASSWORD'
    PUBLICATION $PUBLICATION_NAME;
EOF

if [ $? -eq 0 ]; then
    echo "✓ Subscription created successfully"
else
    echo "✗ Failed to create subscription"
    exit 1
fi
echo ""

# Verify subscription
echo "Verifying subscription status..."
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<EOF
SELECT
    subname AS "Subscription Name",
    subenabled AS "Enabled",
    subslotname AS "Slot Name"
FROM pg_subscription
WHERE subname = '$SUBSCRIPTION_NAME';
EOF
echo ""

echo "Checking replication worker..."
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<EOF
SELECT
    subname AS "Subscription",
    worker_type AS "Worker Type",
    pid AS "PID",
    received_lsn AS "Received LSN",
    last_msg_receipt_time AS "Last Message"
FROM pg_stat_subscription
WHERE subname = '$SUBSCRIPTION_NAME';
EOF
echo ""

echo "=============================================="
echo "✓ Replication setup complete!"
echo ""
echo "To monitor replication:"
echo "  docker compose exec postgres psql -U \$POSTGRES_USER -d \$POSTGRES_DB -c 'SELECT * FROM pg_stat_subscription;'"
echo ""
echo "To check replication logs:"
echo "  docker compose logs postgres | grep -i replication"
echo ""
echo "To pause replication:"
echo "  docker compose exec postgres psql -U \$POSTGRES_USER -d \$POSTGRES_DB -c 'ALTER SUBSCRIPTION $SUBSCRIPTION_NAME DISABLE;'"
echo ""
echo "To resume replication:"
echo "  docker compose exec postgres psql -U \$POSTGRES_USER -d \$POSTGRES_DB -c 'ALTER SUBSCRIPTION $SUBSCRIPTION_NAME ENABLE;'"
