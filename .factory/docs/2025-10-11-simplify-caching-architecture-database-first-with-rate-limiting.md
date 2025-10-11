## Goal
Simplify the caching architecture to a straightforward database-first approach with rate-limited Riot API fallback.

## Current Problems
1. **Complex two-tier caching**: In-memory TTL cache + database caching + data freshness manager
2. **RiotDataManager** has 800+ lines with complex stale data fallback logic
3. **cache.py** has 8 separate TTL cache instances for different data types
4. **Data freshness tracking** adds unnecessary complexity with `data_tracking` table
5. Services don't consistently use the simplified approach

## Simplified Architecture

```
Request → Service → Database Check → [If miss] → Riot API (rate-limited) → Store in DB → Return
                                  → [If hit] → Return from DB
```

### Key Principles
1. **Database is the single source of truth** - No in-memory caching
2. **Rate limiter handles throttling** - Returns `None`/raises exception when rate limited
3. **No TTL freshness checks** - Data in DB is good enough
4. **Services handle flow** - Simple, predictable logic

## Changes Required

### 1. Remove TTL Cache Layer
**Files to modify:**
- `app/riot_api/cache.py` - **DELETE** (remove entirely)
- `app/riot_api/client.py` - Remove all cache references
- `app/riot_api/__init__.py` - Remove cache exports

**Impact:** In-memory caching removed, all data flows through database

### 2. Simplify RiotDataManager
**File:** `app/riot_api/data_manager.py`

**Simplify to:**
- Remove `DataFreshnessManager` class
- Remove `RateLimitAwareFetcher` class
- Remove `SmartFetchStrategy` class
- Remove `StaleDataWarning` dataclass
- Keep only `RiotDataManager` with simple methods:
  - `get_player_by_riot_id()` - Check DB → API → Store
  - `get_player_by_puuid()` - Check DB → API → Store
  - `get_match()` - Check DB → API → Store

**New simple flow:**
```python
async def get_player_by_riot_id(game_name, tag_line, platform):
    # 1. Check database
    player = await self.db.execute(select(Player).where(...))
    if player:
        return player

    # 2. Fetch from API (rate limiter handles throttling)
    try:
        account = await self.api_client.get_account_by_riot_id(game_name, tag_line)
        summoner = await self.api_client.get_summoner_by_puuid(account.puuid, platform)
    except RateLimitError:
        return None  # Or raise exception

    # 3. Store in database
    player = Player(puuid=account.puuid, ...)
    self.db.add(player)
    await self.db.commit()

    return player
```

### 3. Simplify RiotAPIClient
**File:** `app/riot_api/client.py`

**Changes:**
- Remove `self.cache` and all cache-related code
- Remove `enable_cache` parameter
- Remove `cache_hits` and `cache_misses` from stats
- Keep rate limiter functionality intact
- When rate limited (429), raise `RateLimitError` or return `None`

**Rate limit behavior:**
- `wait_if_needed()` waits/sleeps if approaching limits
- If truly rate limited (circuit breaker open), raise `RateLimitError`
- No queuing, no complex fallback logic

### 4. Update Services
**Files:**
- `app/services/players.py` - Use simplified data manager
- `app/services/matches.py` - Use simplified data manager
- `app/services/detection.py` - Use simplified data manager

**Pattern:**
```python
async def get_player_by_riot_id(game_name, tag_line, platform):
    player = await self.data_manager.get_player_by_riot_id(game_name, tag_line, platform)

    if not player:
        raise HTTPException(
            status_code=429,
            detail="Rate limited. Please try again later."
        )

    return PlayerResponse.model_validate(player)
```

### 5. Remove Data Tracking Tables (Optional)
**Files:**
- `app/models/data_tracking.py` - Can be removed
- Database migration - Create migration to drop tables:
  - `data_tracking`
  - `api_request_queue` (if not used elsewhere)

**Alternative:** Keep tables for analytics but don't use them in request flow

### 6. Update Documentation
**Files:**
- `backend/CLAUDE.md` - Update caching strategy section
- `docs/backend-diagrams.md` - Update diagrams to remove TTL cache layer

## Benefits
✅ **Simpler codebase** - Remove ~1000 lines of complex caching logic
✅ **Predictable behavior** - Database or API, no stale data fallbacks
✅ **Easier debugging** - Single data flow path
✅ **PostgreSQL handles caching** - Database is already fast
✅ **Rate limiter stays robust** - Existing rate limiting unchanged
✅ **Clear error handling** - Rate limited = clear error to user

## Trade-offs
⚠️ **More database queries** - No in-memory cache for repeated requests
⚠️ **More API calls** - No TTL-based freshness, every miss hits API
⚠️ **Rate limits hit more often** - Users will see "try again later" more

**Mitigation:** PostgreSQL is very fast for simple lookups. For high-traffic endpoints, can add Redis cache later as a simple key-value layer if needed.

## Implementation Order
1. Remove `cache.py` and cache imports from `client.py` (simple)
2. Simplify `data_manager.py` to 200 lines (complex)
3. Update services to use simplified manager (simple)
4. Update tests to remove cache assertions (simple)
5. Update documentation (simple)
6. (Optional) Drop data_tracking tables via migration

## Testing
- Verify rate limiter still works correctly
- Verify database lookups work
- Verify API calls work when data missing
- Verify 429 errors return properly when rate limited
- Load test to confirm PostgreSQL performance is acceptable
