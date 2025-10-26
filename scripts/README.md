# Scripts

This directory contains utility scripts for development and deployment.

## Available Scripts

### `setup-replication-dev.sh`

Sets up PostgreSQL logical replication from production to your local development environment.

**Purpose:**
- Automatically configure DEV database to replicate data from production
- Test connection to production database
- Create subscription for real-time data sync

**Prerequisites:**
1. Production publication must exist (`prod_to_dev_pub`)
2. Production credentials configured in `.env`
3. Local PostgreSQL running (`docker compose up -d postgres`)

**Usage:**

```bash
# 1. Add credentials to .env (NEVER commit these!)
cat >> .env <<EOF
REPLICATION_PROD_HOST=your_prod_host
REPLICATION_PROD_PORT=your_prod_port
REPLICATION_PROD_USER=your_prod_user
REPLICATION_PROD_PASSWORD=your_prod_password
REPLICATION_PROD_DB=your_prod_db
EOF

# 2. Run the setup script
./scripts/setup-replication-dev.sh
```

**What it does:**
- ✅ Validates all required environment variables
- ✅ Tests connection to production database
- ✅ Checks local PostgreSQL is running
- ✅ Creates logical replication subscription
- ✅ Verifies replication is active
- ✅ Shows replication status

**Environment Variables:**

Required (must be set in `.env`):
- `REPLICATION_PROD_HOST` - Production database host
- `REPLICATION_PROD_PORT` - Production database port
- `REPLICATION_PROD_USER` - Production database user
- `REPLICATION_PROD_PASSWORD` - Production database password
- `REPLICATION_PROD_DB` - Production database name

Optional (defaults provided):
- `REPLICATION_PUBLICATION_NAME` - Publication name (default: `prod_to_dev_pub`)
- `REPLICATION_SUBSCRIPTION_NAME` - Subscription name (default: `dev_from_prod_sub`)

**Documentation:**

See [`docs/postgresql-replication.md`](../docs/postgresql-replication.md) for complete replication setup guide, monitoring, and troubleshooting.

---

## Security Notes

⚠️ **IMPORTANT:**
- Never commit `.env` file to git (already in `.gitignore`)
- Never hardcode production credentials in scripts or documentation
- Production credentials should be shared securely (password manager, encrypted channel)
- Review `.env.example` for all required variables
