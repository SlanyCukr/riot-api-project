# PostgreSQL Database

## Tech Stack
- PostgreSQL 18 database server
- SQLAlchemy async ORM for Python
- Database migrations via Alembic
- pg_dump for backup operations

## Project Structure
- `docker/postgres/init.sql` - Database initialization
- `docker/postgres/postgresql.conf` - PostgreSQL configuration
- `backend/app/models/` - SQLAlchemy model definitions
- `backend/alembic/` - Database migration files
- `postgres-data` volume - Persistent data storage

## Commands
```bash
# Access database shell
docker compose --env-file .env -f docker/docker-compose.yml exec postgres psql -U riot_api_user -d riot_api_db

# Create backup
docker compose --env-file .env -f docker/docker-compose.yml exec postgres pg_dump -U riot_api_user -d riot_api_db > backup.sql

# Restore backup
docker compose --env-file .env -f docker/docker-compose.yml exec -T postgres psql -U riot_api_user -d riot_api_db < backup.sql

# Run migrations
./scripts/migrate.sh

# Reset database (destructive)
./scripts/dev.sh --reset-db
```

## Code Style
- Use parameterized queries via SQLAlchemy
- Follow PostgreSQL naming conventions (snake_case)
- Create indexes for frequently queried columns
- Use foreign key constraints for data integrity

## Do Not
- Run raw SQL strings in application code
- Modify database schema without migrations
- Use reserved SQL keywords for column names
- Skip backups before schema changes
