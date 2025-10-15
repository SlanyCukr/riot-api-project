# Database Migrations

This directory contains SQL migration files for the Riot API database schema.

## Migration Files

- `001_add_player_tracking_columns.sql` - Adds `is_tracked`, `is_analyzed`, and `last_ban_check` columns to the players table

## How to Apply Migrations

### For Running Containers

Apply a migration to a running PostgreSQL container:

```bash
docker exec riot_api_app-postgres-1 psql -U riot_api_user -d riot_api_db -f /docker-entrypoint-initdb.d/migrations/001_add_player_tracking_columns.sql
```

Or copy and run:

```bash
cat docker/postgres/migrations/001_add_player_tracking_columns.sql | \
  docker exec -i riot_api_app-postgres-1 psql -U riot_api_user -d riot_api_db
```

### For Fresh Installations

For new database installations, migrations should be applied automatically during container initialization by adding them to the init process.

To enable automatic migration on fresh install, update `docker-compose.yml` to mount the migrations directory:

```yaml
postgres:
  volumes:
    - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/01-init.sql
    - ./docker/postgres/migrations:/docker-entrypoint-initdb.d/migrations
```

## Creating New Migrations

1. Create a new SQL file with sequential naming: `00X_description.sql`
2. Use `IF NOT EXISTS` or `IF EXISTS` clauses to make migrations idempotent
3. Add appropriate indexes for performance
4. Include comments for documentation
5. Test the migration on a development database first

## Migration Naming Convention

Format: `{number}_{description}.sql`

- Number: 3-digit sequential number (001, 002, 003, etc.)
- Description: Lowercase with underscores, brief and descriptive

Examples:

- `001_add_player_tracking_columns.sql`
- `002_create_match_analysis_table.sql`
- `003_add_rank_indexes.sql`
