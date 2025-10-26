#!/bin/bash
# PostgreSQL Logical Replication Configuration Script
# This script runs during container initialization to enable replication

set -e

# Get the pg_hba.conf location
PG_HBA_FILE=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SHOW hba_file;")

echo "Configuring PostgreSQL for logical replication..."
echo "pg_hba.conf location: $PG_HBA_FILE"

# Add replication access rules to pg_hba.conf
echo "" >> "$PG_HBA_FILE"
echo "# Logical Replication Access (added by configure_replication.sh)" >> "$PG_HBA_FILE"
echo "host    replication     all             0.0.0.0/0               scram-sha-256" >> "$PG_HBA_FILE"
echo "host    all             all             0.0.0.0/0               scram-sha-256" >> "$PG_HBA_FILE"

# Reload PostgreSQL configuration
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT pg_reload_conf();"

echo "Logical replication configuration completed successfully!"
