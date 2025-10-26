# PostgreSQL Logical Replication Setup

This document describes how to set up and use PostgreSQL logical replication to sync data from production to your local development environment.

## Overview

**Logical replication** allows real-time, one-way data synchronization from production to development environments. It replicates DML operations (INSERT, UPDATE, DELETE) while allowing the DEV database to remain writable for testing.

**Key Features:**
- ✅ Real-time data sync from production → development
- ✅ Selective table replication (choose which tables to replicate)
- ✅ DEV environment remains writable (can modify data locally)
- ✅ Production impact is minimal (only creates a replication slot)
- ✅ Automatic setup via Docker Compose (production deployment)

---

## Architecture

```
Production (Publisher)                 Development (Subscriber)
┌──────────────────────┐              ┌──────────────────────┐
│  PostgreSQL 18       │              │  PostgreSQL 18       │
│  Port: 5432 (local)  │──────────────│  Port: 5432          │
│  Port: 5433 (public) │   autossh    │                      │
│                      │   tunnel     │                      │
│  Publication:        │              │  Subscription:       │
│  prod_to_dev_pub     │──────────────▶  dev_from_prod_sub   │
│                      │              │                      │
│  Tables:             │              │  Tables:             │
│  - players           │──replicate──▶  - players           │
│  - matches           │──replicate──▶  - matches           │
│  - ...all tables     │──replicate──▶  - ...all tables     │
└──────────────────────┘              └──────────────────────┘
```

---

## Production Setup (Automatic)

Production is **pre-configured** for logical replication via `compose.prod.yaml`.

### Automatic Configuration

When deploying to production, the following is automatically configured:

1. **PostgreSQL Parameters** (`compose.prod.yaml:compose.prod.yaml:39-44`):
   ```yaml
   command: >
     postgres
     -c shared_preload_libraries=pg_stat_statements
     -c wal_level=logical                  # Enable logical replication
     -c max_replication_slots=30           # Support up to 30 subscriptions
     -c max_wal_senders=30                 # Support up to 30 concurrent streams
   ```

2. **Replication Access** (`docker/postgres/configure_replication.sh`):
   - Automatically configures `pg_hba.conf` to allow replication connections
   - Allows connections from any IP (secured via autossh tunnel)

### Manual Publication Creation

Publications must be created manually on production (one-time setup):

```bash
# SSH to production
ssh riot-prod

# Connect to PostgreSQL
docker compose -f compose.yaml -f compose.prod.yaml exec postgres \
  psql -U riot_api_user -d riot_api_db

# Create publication for all tables
CREATE PUBLICATION prod_to_dev_pub FOR ALL TABLES;

# Verify publication
\dRp+ prod_to_dev_pub

# Exit
\q
```

**Alternative: Selective Table Replication**

To replicate only specific tables:

```sql
CREATE PUBLICATION prod_to_dev_pub FOR TABLE
    players,
    matches,
    match_participants,
    player_ranks;
```

---

## Development Setup (One-Time)

### Prerequisites

- Production publication must be created (see above)
- Production PostgreSQL accessible (via autossh tunnel)
- Production credentials (obtain from team)

### Step 1: Configure Environment Variables

Add production database credentials to your `.env` file:

```bash
# Copy from .env.example if you haven't already
cp .env.example .env

# Edit .env and add replication configuration
nano .env
```

Add these variables (uncomment and fill in values):

```bash
# Production database connection (for replication subscriber)
REPLICATION_PROD_HOST=<production_host>
REPLICATION_PROD_PORT=<production_port>
REPLICATION_PROD_USER=<production_user>
REPLICATION_PROD_PASSWORD=<production_password>
REPLICATION_PROD_DB=<production_database>

# Optional: Override defaults
REPLICATION_PUBLICATION_NAME=prod_to_dev_pub
REPLICATION_SUBSCRIPTION_NAME=dev_from_prod_sub
```

**Security Note:** Never commit `.env` to git! It's already in `.gitignore`.

### Step 2: Run Setup Script

```bash
# Start local PostgreSQL
docker compose up -d postgres

# Run replication setup script
./scripts/setup-replication-dev.sh
```

The script will:
- ✅ Test connection to production
- ✅ Verify local PostgreSQL is running
- ✅ Create subscription
- ✅ Verify replication is active
- ✅ Display status

Expected output:
```
PostgreSQL Logical Replication Setup for DEV
==============================================

Configuration:
  Production Host: <host>
  Production Port: <port>
  Production Database: <database>
  ...

Testing connection to production...
✓ Connection successful

Checking local PostgreSQL...
✓ Local PostgreSQL is running

Creating subscription 'dev_from_prod_sub'...
✓ Subscription created successfully

Verifying subscription status...
 Subscription Name | Enabled | Slot Name
-------------------+---------+-------------------
 dev_from_prod_sub | t       | dev_from_prod_sub

✓ Replication setup complete!
```

### Alternative: Manual Setup

If you prefer to create the subscription manually:

```bash
# Connect to local PostgreSQL
docker compose exec postgres psql -U riot_api_user -d riot_api_db
```

```sql
-- Create subscription to production
CREATE SUBSCRIPTION dev_from_prod_sub
    CONNECTION 'host=<prod_host> port=<prod_port> dbname=<prod_db> user=<prod_user> password=<prod_password>'
    PUBLICATION prod_to_dev_pub;

-- Verify subscription is active
SELECT subname, subenabled, subslotname FROM pg_subscription;

-- Check replication status
SELECT * FROM pg_stat_subscription;
```

### Step 3: Handle Existing Tables

**Important:** Logical replication only replicates **data**, not **schema** (DDL).

#### New Database (No Existing Data)

If your DEV database is empty, the subscription will automatically copy initial data from production.

#### Existing Database (Conflicting Data)

If your DEV database already has data, you may encounter duplicate key errors. Options:

**Option A: Drop and Recreate Tables** (Clean Slate)

```bash
# Stop subscription temporarily
docker compose exec postgres psql -U riot_api_user -d riot_api_db \
  -c "ALTER SUBSCRIPTION dev_from_prod_sub DISABLE;"

# Drop all tables
docker compose exec postgres psql -U riot_api_user -d riot_api_db \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Run migrations to recreate schema
docker compose exec backend uv run alembic upgrade head

# Re-enable subscription and refresh
docker compose exec postgres psql -U riot_api_user -d riot_api_db <<EOF
ALTER SUBSCRIPTION dev_from_prod_sub ENABLE;
ALTER SUBSCRIPTION dev_from_prod_sub REFRESH PUBLICATION WITH (copy_data = true);
EOF
```

**Option B: Keep Existing Data** (Tables Created After Subscription)

For new tables created on production AFTER the subscription:

```sql
-- Refresh subscription to pick up new tables
ALTER SUBSCRIPTION dev_from_prod_sub REFRESH PUBLICATION WITH (copy_data = true);
```

---

## Monitoring Replication

### Check Subscription Status (DEV)

```bash
docker compose exec postgres psql -U riot_api_user -d riot_api_db
```

```sql
-- Basic status
SELECT subname, subenabled FROM pg_subscription;

-- Detailed statistics
SELECT
    subname,
    worker_type,
    pid,
    received_lsn,
    last_msg_receipt_time,
    latest_end_time
FROM pg_stat_subscription;

-- Per-table sync status
SELECT
    srrelid::regclass AS table,
    CASE srsubstate
        WHEN 'i' THEN 'initialize'
        WHEN 'd' THEN 'data copy'
        WHEN 's' THEN 'synchronized'
        WHEN 'r' THEN 'ready'
    END AS state
FROM pg_subscription_rel
WHERE srsubid = (SELECT oid FROM pg_subscription WHERE subname = 'dev_from_prod_sub');
```

### Check Replication Slots (Production)

```bash
ssh riot-prod
docker compose -f compose.yaml -f compose.prod.yaml exec postgres \
  psql -U riot_api_user -d riot_api_db
```

```sql
-- View all replication slots
SELECT
    slot_name,
    slot_type,
    active,
    confirmed_flush_lsn
FROM pg_replication_slots;

-- Check main subscription slot (should be active)
SELECT * FROM pg_replication_slots WHERE slot_name = 'dev_from_prod_sub';
```

### Check Replication Logs (DEV)

```bash
docker compose logs postgres | grep -i "replication\|subscription"
```

---

## Common Operations

### Pause Replication

```bash
docker compose exec postgres psql -U riot_api_user -d riot_api_db \
  -c "ALTER SUBSCRIPTION dev_from_prod_sub DISABLE;"
```

### Resume Replication

```bash
docker compose exec postgres psql -U riot_api_user -d riot_api_db \
  -c "ALTER SUBSCRIPTION dev_from_prod_sub ENABLE;"
```

### Add New Tables to Replication

When new tables are added to production:

```sql
-- On production: Add table to publication (if using selective replication)
ALTER PUBLICATION prod_to_dev_pub ADD TABLE new_table_name;

-- On DEV: Refresh subscription
ALTER SUBSCRIPTION dev_from_prod_sub REFRESH PUBLICATION WITH (copy_data = true);
```

### Remove Subscription (DEV)

```bash
docker compose exec postgres psql -U riot_api_user -d riot_api_db \
  -c "DROP SUBSCRIPTION dev_from_prod_sub;"
```

**Note:** This also drops the replication slot on production automatically.

---

## Testing Replication

### Test INSERT

```bash
# On production: Insert data
ssh riot-prod
docker compose -f compose.yaml -f compose.prod.yaml exec postgres \
  psql -U riot_api_user -d riot_api_db \
  -c "INSERT INTO players (name, region) VALUES ('TestPlayer', 'eun1') RETURNING *;"

# On DEV: Verify replication (wait 1-2 seconds)
docker compose exec postgres psql -U riot_api_user -d riot_api_db \
  -c "SELECT * FROM players WHERE name = 'TestPlayer';"
```

### Test UPDATE

```bash
# On production: Update data
ssh riot-prod
docker compose -f compose.yaml -f compose.prod.yaml exec postgres \
  psql -U riot_api_user -d riot_api_db \
  -c "UPDATE players SET name = 'UpdatedPlayer' WHERE name = 'TestPlayer' RETURNING *;"

# On DEV: Verify replication
docker compose exec postgres psql -U riot_api_user -d riot_api_db \
  -c "SELECT * FROM players WHERE name = 'UpdatedPlayer';"
```

### Test DELETE

```bash
# On production: Delete data
ssh riot-prod
docker compose -f compose.yaml -f compose.prod.yaml exec postgres \
  psql -U riot_api_user -d riot_api_db \
  -c "DELETE FROM players WHERE name = 'UpdatedPlayer' RETURNING *;"

# On DEV: Verify deletion
docker compose exec postgres psql -U riot_api_user -d riot_api_db \
  -c "SELECT * FROM players WHERE name = 'UpdatedPlayer';"
# Should return 0 rows
```

---

## Troubleshooting

### Subscription Not Replicating

**Check subscription is enabled:**

```sql
SELECT subname, subenabled FROM pg_subscription;
```

If `subenabled = f`, enable it:

```sql
ALTER SUBSCRIPTION dev_from_prod_sub ENABLE;
```

**Check for errors in logs:**

```bash
docker compose logs postgres | grep -i error
```

### Duplicate Key Errors

If you see errors like `duplicate key value violates unique constraint`:

1. Your DEV database has existing data conflicting with production
2. Options:
   - Drop conflicting tables and refresh subscription
   - Manually resolve conflicts by deleting conflicting rows

### Replication Slot Full (Production)

If you see `ERROR: all replication slots are in use`:

```bash
# On production: Increase max_replication_slots (already set to 30 in compose.prod.yaml)
# Check current usage:
ssh riot-prod
docker compose -f compose.yaml -f compose.prod.yaml exec postgres \
  psql -U riot_api_user -d riot_api_db \
  -c "SELECT COUNT(*) FROM pg_replication_slots;"

# Drop unused slots (if any)
# SELECT pg_drop_replication_slot('slot_name');
```

### Connection Refused

If you see `connection refused` when creating subscription:

1. Check autossh tunnel is running on production
2. Verify production port is accessible: `telnet $REPLICATION_PROD_HOST $REPLICATION_PROD_PORT`
3. Check production PostgreSQL is running: `ssh riot-prod && docker compose ps`

### Replication Lag

Check lag between production and DEV:

```sql
-- On DEV
SELECT
    subname,
    pg_wal_lsn_diff(received_lsn, latest_end_lsn) AS lag_bytes,
    last_msg_receipt_time,
    latest_end_time
FROM pg_stat_subscription;
```

---

## Best Practices

✅ **Do:**
- Use replication for development environment synchronization
- Monitor replication lag regularly
- Test replication after major schema changes
- Keep max_replication_slots = 30 (supports multiple devs + table sync slots)

❌ **Don't:**
- Rely on replication for backups (use pg_dump instead)
- Replicate sensitive production data to untrusted environments
- Use bidirectional replication (production ← → dev) without careful planning
- Delete replication slots manually (use DROP SUBSCRIPTION instead)

---

## References

- [PostgreSQL 18 Logical Replication Documentation](https://www.postgresql.org/docs/18/logical-replication.html)
- [PostgreSQL 18 Replication Configuration](https://www.postgresql.org/docs/18/runtime-config-replication.html)
- [Production Server Documentation](./production-rpi.md)
- [Docker Compose Commands](../docker/AGENTS.md)
