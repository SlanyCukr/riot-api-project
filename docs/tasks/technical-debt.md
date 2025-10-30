# Technical Debt

This document tracks known technical debt items and planned improvements for the Riot API project.

## Authentication & Security

### Refresh Tokens

**Priority:** High
**Status:** Planned
**Description:** Implement refresh token mechanism for long-lived sessions without compromising security.

**Current State:**

- JWT access tokens have 7-day expiration
- No refresh token implementation
- Logout is client-side only (no token revocation)

**Proposed Solution:**

- Implement short-lived access tokens (15-60 minutes)
- Add refresh token system with rotation
- Store refresh tokens in database with expiration tracking
- Implement token revocation on logout

**References:**

- [OAuth 2.0 Refresh Tokens](https://oauth.net/2/refresh-tokens/)
- [JWT Best Practices - Refresh Tokens](https://auth0.com/blog/refresh-tokens-what-are-they-and-when-to-use-them/)

---

### JWT Token Revocation / Blacklisting

**Priority:** High
**Status:** Planned
**Description:** Implement token revocation mechanism to invalidate JWTs before expiration.

**Current State:**

- JWTs are stateless and cannot be revoked
- Logout endpoint is placeholder (`backend/app/features/auth/router.py:58`)
- Compromised tokens remain valid until expiration

**Proposed Solution:**

- Implement Redis-based token blacklist
- Add revoked token check in authentication middleware
- Revoke tokens on logout, password change, and admin actions
- Automatic cleanup of expired blacklist entries

**Alternative:**

- Use short-lived tokens + refresh tokens (see above)
- Token rotation on each request

---

### Account Lockout Mechanism

**Priority:** Medium
**Status:** Planned
**Description:** Implement account lockout after multiple failed login attempts to prevent brute force attacks.

**Current State:**

- Rate limiting implemented (5 login attempts/minute per IP)
- No per-account lockout mechanism
- Attackers can try slowly over time

**Proposed Solution:**

- Track failed login attempts per user account in database
- Lock account after N failed attempts (e.g., 5 attempts)
- Implement time-based unlock (e.g., 15 minutes) or require admin unlock
- Send email notification on account lockout
- Reset failed attempt counter on successful login

**Database Changes:**

```sql
ALTER TABLE auth.users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE auth.users ADD COLUMN locked_until TIMESTAMP;
ALTER TABLE auth.users ADD COLUMN last_failed_login TIMESTAMP;
```

---

### JWT Secret Key Validation

**Priority:** High
**Status:** Research Completed
**Description:** Implement runtime validation for JWT secret key in production.

**Current State:**

- Default JWT secret includes warning message (`backend/app/core/config.py:65-67`)
- No runtime check if secret is changed in production
- Risk of deploying with default secret

**Research Findings (2025):**

**Secret Generation Methods:**

1. **Python secrets module** (Recommended):

   ```python
   import secrets
   secret_key = secrets.token_hex(32)  # 256-bit key
   # or
   secret_key = secrets.token_urlsafe(32)
   ```

2. **OpenSSL command**:

   ```bash
   openssl rand -hex 32
   ```

3. **NEVER use**:
   - `random` module (not cryptographically secure)
   - UUIDs (not cryptographically secure)

**Security Best Practices:**

- Rotate keys every 3-6 months, or immediately after security incident
- Consider RS256 (asymmetric) instead of HS256 for better security
- Never commit keys to version control
- Always use environment variables for production

**Proposed Implementation:**

1. Add startup validation in `backend/app/main.py`:

   ```python
   if settings.environment == "production":
       if "dev_secret" in settings.jwt_secret_key.lower():
           raise ValueError("Production JWT secret must be changed!")
       if len(settings.jwt_secret_key) < 32:
           raise ValueError("JWT secret must be at least 32 characters!")
   ```

2. Document secret generation in deployment docs:
   - Add instructions to generate secret using `secrets.token_hex(32)`
   - Recommend Docker secrets integration for containerized deployments
   - Document AWS Secrets Manager / Azure Key Vault integration
   - Add key rotation procedures

**References:**

- [Secure JWT Key Generation 2025](https://theriturajps.github.io/blog/generate-jwt-secret-keys-secure-2025)
- [Auth0: JWT Handling in Python](https://auth0.com/blog/how-to-handle-jwt-in-python/)
- [FastAPI OAuth2 JWT Tutorial](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)

---

## Secrets Management

### File-Based Secrets (Docker Compose Secrets)

**Priority:** High
**Status:** Planned
**Description:** Move from environment variables to file-based secrets for improved security.

**Current State:**

- All secrets (JWT, database credentials, Riot API key) passed via environment variables
- Environment variables visible via `docker inspect` and `docker exec`
- Can leak in application logs during crashes
- No encryption at rest on host system
- Validated on startup since implementing JWT secret validator (`backend/app/core/config.py:75`)

**Security Risks of Current Approach:**

1. **Visibility**: Anyone with container access can view secrets via `docker inspect` or `ps`
2. **Log Leakage**: Secrets can appear in error dumps and application logs
3. **Process Exposure**: Environment variables visible to all processes in container
4. **No Encryption**: Stored in plaintext in `.env` file (though gitignored)
5. **No Audit Trail**: No tracking of who accessed secrets or when

**Proposed Solution (Tier 2):**
Implement Docker Compose secrets with file-based approach:

```yaml
# compose.prod.yaml
services:
  backend:
    secrets:
      - jwt_secret_key
      - postgres_password
    environment:
      # Point to secret files instead of direct values
      JWT_SECRET_KEY_FILE: /run/secrets/jwt_secret_key
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password

secrets:
  jwt_secret_key:
    file: ./secrets/jwt_secret_key.txt # Local file, gitignored
  postgres_password:
    file: ./secrets/postgres_password.txt
```

**Benefits:**

- Secrets stored as separate files with restricted file permissions
- Not visible via `docker inspect` or environment variable dumps
- Can use file permissions to restrict access (`chmod 600`)
- Works with Docker Compose v3.1+ (no Swarm mode required)
- Significantly more secure than environment variables

**Limitations:**

- Still stored as plaintext files on host (protected by file permissions)
- Not encrypted at rest (requires Swarm mode or external manager)
- Manual file management required

**Implementation Steps:**

1. Create `secrets/` directory in project root, add to `.gitignore`
2. Generate and save secrets to files:
   ```bash
   mkdir -p secrets
   chmod 700 secrets
   python -c 'import secrets; print(secrets.token_hex(32))' > secrets/jwt_secret_key.txt
   chmod 600 secrets/*.txt
   ```
3. Update `backend/app/core/config.py` to support `*_FILE` environment variables:
   ```python
   @property
   def jwt_secret_key_value(self) -> str:
       """Get JWT secret from file or environment variable."""
       file_path = os.getenv("JWT_SECRET_KEY_FILE")
       if file_path and os.path.exists(file_path):
           with open(file_path) as f:
               return f.read().strip()
       return self.jwt_secret_key
   ```
4. Update `compose.prod.yaml` with secrets configuration
5. Update deployment documentation

**References:**

- [Docker Compose Secrets Documentation](https://docs.docker.com/compose/use-secrets/)
- [Bitdoze: Docker Compose Secrets Guide](https://www.bitdoze.com/docker-compose-secrets/)

---

### External Secrets Managers (Advanced)

**Priority:** Medium
**Status:** Future Enhancement
**Description:** Integrate with external secrets management service for production-grade security.

**When Needed:**

- Deploying at scale (multiple servers)
- Handling sensitive PII or payment data
- Regulatory compliance requirements (SOC 2, HIPAA, etc.)
- Need for audit trails and access logs
- Automatic secret rotation

**Options:**

**1. Docker Swarm Secrets** (if using Swarm orchestration)

- Built into Docker Swarm mode
- Fully encrypted at rest and in transit
- Mounted in `/run/secrets/` as tmpfs (never written to disk)
- Automatic distribution across Swarm cluster
- **Limitation**: Requires enabling Swarm mode

**2. HashiCorp Vault**

- Self-hosted or cloud
- Dynamic secrets with automatic rotation
- Fine-grained access control
- Full audit logging
- Supports multiple authentication backends
- **Complexity**: Requires separate infrastructure

**3. Cloud Provider Secrets**

- **AWS Secrets Manager**: Automatic rotation, tight IAM integration
- **Azure Key Vault**: Integration with Azure services
- **Google Secret Manager**: Integration with GCP services
- **Pros**: Managed service, no infrastructure to maintain
- **Cons**: Vendor lock-in, additional cost

**Implementation Considerations:**

- Add Python client library (boto3 for AWS, azure-keyvault for Azure, etc.)
- Update `Settings` class to fetch secrets on startup
- Implement caching to avoid API calls on every request
- Handle secret rotation gracefully (watch for updates)
- Consider using application-side secret caching with TTL

**Example (AWS Secrets Manager):**

```python
import boto3
from botocore.exceptions import ClientError

def get_secret_from_aws(secret_name: str) -> str:
    """Fetch secret from AWS Secrets Manager."""
    client = boto3.client('secretsmanager', region_name='us-east-1')
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        raise RuntimeError(f"Failed to fetch secret: {e}")
```

---

### Database Credentials Migration

**Priority:** High
**Status:** Planned
**Description:** Move database credentials (POSTGRES_PASSWORD, POSTGRES_USER) from environment variables to Docker secrets.

**Current State:**

- Database credentials in `.env` file and passed via environment variables
- Exposed to all processes in containers
- Visible via `docker inspect`

**Proposed Solution:**

1. **Phase 1**: Move to file-based Docker Compose secrets (Tier 2)
   - Store `POSTGRES_PASSWORD` in `secrets/postgres_password.txt`
   - Update compose files to use secrets
   - Update PostgreSQL container to read from `/run/secrets/`
2. **Phase 2**: Consider external secrets manager (Tier 3) if needed

**Database Container Support:**
PostgreSQL official image supports reading secrets from files:

```yaml
services:
  postgres:
    secrets:
      - postgres_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password

secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
```

**Backend Application:**
Update connection string construction to read from secret file:

```python
def get_database_url(self) -> str:
    """Construct database URL with secrets from files."""
    password_file = os.getenv("POSTGRES_PASSWORD_FILE")
    if password_file and os.path.exists(password_file):
        with open(password_file) as f:
            password = f.read().strip()
    else:
        password = self.postgres_password

    return f"postgresql+asyncpg://{self.postgres_user}:{password}@postgres:5432/{self.postgres_db}"
```

---

### Deprecate Riot API Key from Environment Variables

**Priority:** Medium
**Status:** ✅ Completed (2025-10-26)
**Description:** Removed Riot API key from `.env` file; now uses database-only storage.

**Implementation Details:**

- Removed `riot_api_key` field from `Settings` class in `backend/app/core/config.py`
- `get_riot_api_key(db)` function now retrieves from database only
- Updated all documentation to reflect database-only storage
- Removed `RIOT_API_KEY` from `.env.example`

**Rationale for Database-Only Storage:**

1. **Runtime Updates**: API keys can be updated via web UI without redeployment
2. **Key Rotation**: Easy to rotate keys without container restarts
3. **No .env Dependency**: Reduces reliance on environment variables
4. **Centralized Management**: Single source of truth for API key
5. **Development Keys Expire**: Riot development keys expire every 24 hours, need frequent updates

**What Was Changed:**

1. **Backend Configuration** (`backend/app/core/config.py`):

   - Removed `riot_api_key` field from `Settings` class
   - `get_riot_api_key(db)` function retrieves from database only
   - Raises clear error if API key not configured in database

2. **Documentation Updates**:

   - Removed `RIOT_API_KEY` from `.env.example`
   - Updated `README.md` setup instructions
   - Updated `docker/AGENTS.md` environment variables section
   - Updated `docs/production.md` secrets section
   - Updated `backend/README.md` key variables list
   - Updated `backend/app/core/AGENTS.md` configuration docs

3. **User Experience**:
   - API key set via web UI at `/settings` page
   - Startup logs warn if API key not configured
   - Clear error messages guide users to settings page

**Benefits Achieved:**

- ✅ Single source of truth for API key (database)
- ✅ Runtime key updates without container restarts
- ✅ No sensitive data in `.env` files
- ✅ Simpler deployment process
- ✅ Supports 24-hour dev key rotation workflow

**Migration for Existing Users:**

Users with API key in `.env` should:

1. Set API key via web UI at `/settings`
2. Remove `RIOT_API_KEY` line from `.env`
3. Restart services

---

## Frontend

### CSRF Protection

**Priority:** Medium
**Status:** Planned
**Description:** Implement CSRF protection for state-changing operations.

**Current State:**

- JWT tokens stored in both localStorage AND cookies
- Cookies do not have `httpOnly` or `secure` flags set
- No CSRF token implementation

**Proposed Solution:**

- Choose ONE storage mechanism (localStorage or cookies, not both)
- If using cookies:
  - Enable `httpOnly` flag (prevent XSS)
  - Enable `secure` flag (HTTPS only)
  - Implement CSRF tokens for state-changing operations
- If using localStorage:
  - Remove cookie storage entirely
  - Accept XSS risk (mitigated by CSP headers)

**Code Locations:**

- `frontend/features/auth/context/auth-context.tsx:52-54, 105-107`

---

## Database

### Password Hash Column Size

**Status:** Completed
**Description:** Changed `auth.users.password_hash` from `String(255)` to `Text` type to future-proof against longer Argon2 hashes with different parameters.

**Migration:** See Alembic migration `XXX_change_password_hash_to_text.py`

---

## Performance

_No current performance-related technical debt items._

---

## Testing

_No current testing-related technical debt items._

---

## Documentation

### Admin User Management

**Status:** Completed
**Description:** Created unified `backend/scripts/manage_admin.py` to manage admin user accounts.

**Usage:**

```bash
# Create a new admin user
docker compose exec backend uv run python scripts/manage_admin.py create

# Reset an existing admin user's password
docker compose exec backend uv run python scripts/manage_admin.py reset
```

---

## Contributing to This Document

When adding technical debt items:

1. Use clear, descriptive headings
2. Include priority level (High/Medium/Low)
3. Document current state and proposed solution
4. Reference relevant code locations
5. Link to external resources when helpful
6. Update status as work progresses
7. Move completed items to bottom with "Completed" status

**Priority Levels:**

- **High:** Security risks, data integrity issues, or major performance problems
- **Medium:** Quality of life improvements, moderate security enhancements
- **Low:** Nice-to-have features, minor refactoring opportunities
