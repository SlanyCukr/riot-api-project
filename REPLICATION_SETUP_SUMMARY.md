# PostgreSQL Replication Setup - Summary

## ✅ Completed Tasks

### 1. Production Configuration (Automatic on Deployment)

**Modified Files:**

- `compose.prod.yaml` - Added logical replication parameters to PostgreSQL command
- `docker/postgres/configure_replication.sh` - Auto-configures `pg_hba.conf` on fresh deployments

**What's Configured:**

- ✅ `wal_level = logical` (enables logical replication)
- ✅ `max_replication_slots = 30` (supports multiple subscriptions)
- ✅ `max_wal_senders = 30` (supports concurrent streams)
- ✅ Replication access via `pg_hba.conf` (new deployments only)

### 2. Development Setup (Automated Script)

**Created Files:**

- `scripts/setup-replication-dev.sh` - Automated replication setup for DEV
- `scripts/README.md` - Documentation for setup script

**What the Script Does:**

- ✅ Reads credentials from `.env` (no hardcoded secrets)
- ✅ Tests connection to production
- ✅ Creates subscription automatically
- ✅ Verifies replication is working

### 3. Security Improvements

**Modified Files:**

- `.env.example` - Added replication variables (commented, no actual credentials)
- `docs/postgresql-replication.md` - Removed all hardcoded credentials

**Security Measures:**

- ✅ All credentials moved to `.env` (already in `.gitignore`)
- ✅ No hardcoded passwords in code or documentation
- ✅ Script validates credentials before use

### 4. Documentation

**Created/Modified Files:**

- `docs/postgresql-replication.md` - Complete replication guide
  - Architecture overview
  - Setup instructions
  - Monitoring and troubleshooting
  - Best practices

---

## Current Status

### Production (Already Configured)

- ✅ Logical replication enabled (`wal_level = logical`)
- ✅ Replication slots configured (30 max)
- ✅ `pg_hba.conf` allows replication connections
- ✅ Publication created: `prod_to_dev_pub`

### Development (Active Replication)

- ✅ Subscription created: `dev_from_prod_sub`
- ✅ Real-time replication working
- ✅ Tested: INSERT, UPDATE, DELETE operations

---

## How to Use (For Team Members)

### New Developer Setup

1. **Get production credentials** (securely, not from git)

2. **Add to `.env`:**

   ```bash
   # Edit your local .env file
   nano .env

   # Add these lines (replace with actual values)
   REPLICATION_PROD_HOST=<prod_host>
   REPLICATION_PROD_PORT=<prod_port>
   REPLICATION_PROD_USER=<prod_user>
   REPLICATION_PROD_PASSWORD=<prod_password>
   REPLICATION_PROD_DB=<prod_db>
   ```

3. **Run setup script:**

   ```bash
   docker compose up -d postgres
   ./scripts/setup-replication-dev.sh
   ```

4. **Done!** Your DEV database now syncs from production in real-time.

---

## Files Modified/Created

### Modified

- `compose.prod.yaml` - Added replication config to PostgreSQL
- `.env.example` - Added replication variables (template)
- `docs/postgresql-replication.md` - Removed hardcoded credentials

### Created

- `docker/postgres/configure_replication.sh` - Auto-setup script (new deployments)
- `scripts/setup-replication-dev.sh` - DEV setup automation
- `scripts/README.md` - Scripts documentation
- `docs/postgresql-replication.md` - Complete replication guide

---

## Next Steps

### Immediate

- ✅ Nothing! Replication is fully configured and working

### Future Production Deployment

When you redeploy production:

1. **Automatic:** Replication settings will be applied via `compose.prod.yaml`
2. **Manual (one-time):** Recreate publication:
   ```bash
   ssh riot-prod
   docker compose -f compose.yaml -f compose.prod.yaml exec postgres \
     psql -U riot_api_user -d riot_api_db \
     -c "CREATE PUBLICATION prod_to_dev_pub FOR ALL TABLES;"
   ```

---

## Security Reminders

⚠️ **NEVER:**

- Commit `.env` to git
- Share credentials in chat/email (use password manager)
- Hardcode credentials in code or docs

✅ **ALWAYS:**

- Use `.env` for credentials
- Share credentials securely (encrypted)
- Review changes before committing

---

## Monitoring Replication

```bash
# Check subscription status
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "SELECT * FROM pg_stat_subscription;"

# View replication logs
docker compose logs postgres | grep -i replication

# Check replication lag
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "SELECT subname, pg_wal_lsn_diff(received_lsn, latest_end_lsn) AS lag_bytes FROM pg_stat_subscription;"
```

---

## Documentation

- **Setup Guide:** `docs/postgresql-replication.md`
- **Script Docs:** `scripts/README.md`
- **Production Docs:** `docs/production.md`
- **Docker Commands:** `docker/AGENTS.md`

---

## Tested Operations

All replication operations verified:

| Operation | Production | DEV | Status  |
| --------- | ---------- | --- | ------- |
| INSERT    | ✅         | ✅  | Working |
| UPDATE    | ✅         | ✅  | Working |
| DELETE    | ✅         | ✅  | Working |

**Replication Lag:** <1 second (real-time)

---

This setup is complete and ready for use! 🎉
