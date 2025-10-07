# Riot API Reference

Quick reference for Riot Games API endpoints used in this project. This document focuses on League of Legends endpoints for player data, match history, and ranked information.

## Table of Contents

1. [Authentication](#authentication)
2. [Rate Limiting](#rate-limiting)
3. [Regional & Platform Routing](#regional--platform-routing)
4. [Core Endpoints](#core-endpoints)
   - [Account-v1](#account-v1-riot-id-regional)
   - [Summoner-v4](#summoner-v4-platform)
   - [Match-v5](#match-v5-regional)
   - [League-v4](#league-v4-platform)
   - [Spectator-v4](#spectator-v4-platform)
5. [Data Models](#data-models)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)

---

## Authentication

### API Key Types

**Development Keys:**
- Automatically generated when you create a Developer Portal account at https://developer.riotgames.com/
- **Expire every 24 hours** - must be regenerated daily
- Against developer policies to use in production
- Rate limits: 20 requests/second, 100 requests/2 minutes

**Personal Keys:**
- For products intended for developer or small private community
- Do not expire
- Can be registered without verification
- Won't be approved for rate limit increases

**Production Keys:**
- For products intended for large communities or public use
- Do not expire
- Much higher rate limits
- Requires working prototype before approval

### Header Format

All API requests require authentication via the `X-Riot-Token` header:

```bash
GET /riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}
Host: europe.api.riotgames.com
X-Riot-Token: RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

Alternative: Pass as query parameter (not recommended):
```
?api_key=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

---

## Rate Limiting

### Development Key Limits

- **Application Rate Limit**: 20 requests every 1 second
- **Application Rate Limit**: 100 requests every 2 minutes
- Rate limits are enforced **per API key** and **per region**

### Rate Limit Types

1. **Application Rate Limits**: Per API key per region, counts all endpoint calls
2. **Method Rate Limits**: Per specific endpoint method
3. **Service Rate Limits**: Underlying service limits (may not include `X-Rate-Limit-Type` header)

### Rate Limit Headers

Response headers communicate rate limit status:
- `X-App-Rate-Limit`: Application rate limit configuration
- `X-App-Rate-Limit-Count`: Current application rate limit usage
- `X-Method-Rate-Limit`: Method rate limit configuration
- `X-Method-Rate-Limit-Count`: Current method rate limit usage
- `X-Rate-Limit-Type`: Type of rate limit (application/method/service)

### Handling 429 Responses

When you receive a `429 Rate Limit Exceeded` response:

1. **Check `Retry-After` header**: Halt API calls for the duration in seconds
2. **Implement exponential backoff**: Don't immediately retry
3. **Respect rate limits**: Applications that routinely violate may have access disabled

Example 429 Response:
```json
{
  "status": {
    "status_code": 429,
    "message": "Rate limit exceeded"
  }
}
```

**Important**: Rate limits are per region. With 20 req/sec limit, you can make 20 req/sec to NA AND 20 req/sec to EUW simultaneously.

---

## Regional & Platform Routing

### Regional Routing Values

Used for Account-v1 and Match-v5 APIs:

| Region | Host | Coverage |
|--------|------|----------|
| AMERICAS | `americas.api.riotgames.com` | North & South America |
| EUROPE | `europe.api.riotgames.com` | Europe, Russia, Turkey, Middle East |
| ASIA | `asia.api.riotgames.com` | Korea, Japan |
| SEA | `sea.api.riotgames.com` | Southeast Asia, Oceania, Taiwan |

### Platform Routing Values

Used for Summoner-v4, League-v4, and Spectator-v4 APIs:

| Platform | Host | Server Name |
|----------|------|-------------|
| EUN1 | `eun1.api.riotgames.com` | Europe Nordic & East |
| EUW1 | `euw1.api.riotgames.com` | Europe West |
| NA1 | `na1.api.riotgames.com` | North America |
| KR | `kr.api.riotgames.com` | Korea |
| BR1 | `br1.api.riotgames.com` | Brazil |
| LA1 | `la1.api.riotgames.com` | Latin America North |
| LA2 | `la2.api.riotgames.com` | Latin America South |
| OC1 | `oc1.api.riotgames.com` | Oceania |
| RU | `ru.api.riotgames.com` | Russia |
| TR1 | `tr1.api.riotgames.com` | Turkey |
| JP1 | `jp1.api.riotgames.com` | Japan |
| PH2 | `ph2.api.riotgames.com` | Philippines |
| SG2 | `sg2.api.riotgames.com` | Singapore |
| TH2 | `th2.api.riotgames.com` | Thailand |
| TW2 | `tw2.api.riotgames.com` | Taiwan |
| VN2 | `vn2.api.riotgames.com` | Vietnam |

### When to Use Each Type

- **Regional routing**: For Match-v5 (match history, match details) and Account-v1 (Riot ID lookups)
- **Platform routing**: For Summoner-v4, League-v4 (ranked info), and Spectator-v4 (live games)

**Important**: PUUIDs are globally unique and don't change when a player transfers regions.

---

## Core Endpoints

### Account-v1 (Riot ID) [Regional]

**Purpose**: Retrieve account information using Riot ID (gameName#tagLine) or PUUID.

**Important**: This is the **recommended** method for player identification. Summoner names are deprecated.

#### Get Account by Riot ID

```
GET /riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}
Host: {region}.api.riotgames.com
```

**Path Parameters:**
- `gameName` (string): In-game name (before the #)
- `tagLine` (string): Tag line (after the #)

**Example Request:**
```bash
GET /riot/account/v1/accounts/by-riot-id/smile/6578
Host: europe.api.riotgames.com
X-Riot-Token: RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**Example Response:**
```json
{
  "puuid": "jUr1OkZKAS4AW6amrpxOmfYin3w9P-jiVuI7UtNmyrJRL9Z5B0R_Qzs6h7pEwCThABtBODsoyhcDbQ",
  "gameName": "smile",
  "tagLine": "6578"
}
```

#### Get Account by PUUID

```
GET /riot/account/v1/accounts/by-puuid/{puuid}
Host: {region}.api.riotgames.com
```

**Path Parameters:**
- `puuid` (string): Player Universally Unique Identifier

**Example Request:**
```bash
GET /riot/account/v1/accounts/by-puuid/jUr1OkZKAS4AW6amrpxOmfYin3w9P-jiVuI7UtNmyrJRL9Z5B0R_Qzs6h7pEwCThABtBODsoyhcDbQ
Host: europe.api.riotgames.com
X-Riot-Token: RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

---

### Summoner-v4 [Platform]

**Purpose**: Retrieve League of Legends summoner information including encrypted summoner ID needed for League-v4 and Spectator-v4 endpoints.

**Deprecation Warning**: `/lol/summoner/v4/summoners/by-name/{summonerName}` is **DEPRECATED** and may return 403 with development keys. Use Account-v1 to get PUUID, then use `by-puuid` endpoint.

#### Get Summoner by PUUID (Recommended)

```
GET /lol/summoner/v4/summoners/by-puuid/{encryptedPUUID}
Host: {platform}.api.riotgames.com
```

**Path Parameters:**
- `encryptedPUUID` (string): Player UUID from Account-v1

**Example Request:**
```bash
GET /lol/summoner/v4/summoners/by-puuid/jUr1OkZKAS4AW6amrpxOmfYin3w9P-jiVuI7UtNmyrJRL9Z5B0R_Qzs6h7pEwCThABtBODsoyhcDbQ
Host: eun1.api.riotgames.com
X-Riot-Token: RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**Example Response:**
```json
{
  "id": "encrypted_summoner_id_here",
  "accountId": "encrypted_account_id_here",
  "puuid": "jUr1OkZKAS4AW6amrpxOmfYin3w9P-jiVuI7UtNmyrJRL9Z5B0R_Qzs6h7pEwCThABtBODsoyhcDbQ",
  "name": "OldSummonerName",
  "profileIconId": 4568,
  "revisionDate": 1640995200000,
  "summonerLevel": 150
}
```

**Note**: The `name` field contains **stale data** as of November 20, 2023. Use Account-v1 for current Riot ID.

#### Get Summoner by Name (Deprecated)

```
GET /lol/summoner/v4/summoners/by-name/{summonerName}
Host: {platform}.api.riotgames.com
```

**Status**: DEPRECATED - Will be removed in future. May return 403 with development keys.

---

### Match-v5 [Regional]

**Purpose**: Retrieve match history and detailed match data.

#### Get Match IDs by PUUID

```
GET /lol/match/v5/matches/by-puuid/{puuid}/ids
Host: {region}.api.riotgames.com
```

**Path Parameters:**
- `puuid` (string): Player UUID

**Query Parameters:**
- `start` (int, optional): Starting index (default: 0)
- `count` (int, optional): Number of match IDs to return (default: 20, max: 100)
- `startTime` (long, optional): Epoch timestamp in seconds (only matches after this time)
- `endTime` (long, optional): Epoch timestamp in seconds (only matches before this time)
- `queue` (int, optional): Queue ID filter (e.g., 420 for Ranked Solo, 440 for Ranked Flex)
- `type` (string, optional): Match type filter (e.g., "ranked", "normal", "tourney", "tutorial")

**Example Request:**
```bash
GET /lol/match/v5/matches/by-puuid/jUr1OkZKAS4AW6amrpxOmfYin3w9P-jiVuI7UtNmyrJRL9Z5B0R_Qzs6h7pEwCThABtBODsoyhcDbQ/ids?start=0&count=20
Host: europe.api.riotgames.com
X-Riot-Token: RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**Example Response:**
```json
[
  "EUW1_6234567890",
  "EUW1_6234567889",
  "EUW1_6234567888"
]
```

#### Get Match by ID

```
GET /lol/match/v5/matches/{matchId}
Host: {region}.api.riotgames.com
```

**Path Parameters:**
- `matchId` (string): Match identifier (format: `{platform}_{gameId}`)

**Example Request:**
```bash
GET /lol/match/v5/matches/EUW1_6234567890
Host: europe.api.riotgames.com
X-Riot-Token: RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**Example Response:**
```json
{
  "metadata": {
    "matchId": "EUW1_6234567890",
    "dataVersion": "2",
    "participants": [
      "puuid1",
      "puuid2",
      "puuid3",
      "puuid4",
      "puuid5",
      "puuid6",
      "puuid7",
      "puuid8",
      "puuid9",
      "puuid10"
    ]
  },
  "info": {
    "gameCreation": 1640995200000,
    "gameDuration": 1856,
    "gameStartTimestamp": 1640995300000,
    "gameEndTimestamp": 1640997156000,
    "gameId": 6234567890,
    "gameMode": "CLASSIC",
    "gameName": "teambuilder-match-6234567890",
    "gameType": "MATCHED_GAME",
    "gameVersion": "12.1.123.4567",
    "mapId": 11,
    "platformId": "EUW1",
    "queueId": 420,
    "tournamentCode": "",
    "participants": [
      {
        "puuid": "puuid1",
        "summonerName": "PlayerOne",
        "summonerId": "encrypted_summoner_id",
        "championName": "Yasuo",
        "championId": 157,
        "teamId": 100,
        "teamPosition": "MIDDLE",
        "individualPosition": "MIDDLE",
        "win": true,
        "kills": 12,
        "deaths": 3,
        "assists": 8,
        "champLevel": 18,
        "goldEarned": 15000,
        "totalMinionsKilled": 180,
        "neutralMinionsKilled": 20,
        "visionScore": 25,
        "challenges": {},
        "perks": {}
      }
    ],
    "teams": [
      {
        "teamId": 100,
        "win": true,
        "bans": [],
        "objectives": {}
      },
      {
        "teamId": 200,
        "win": false,
        "bans": [],
        "objectives": {}
      }
    ]
  }
}
```

**Important**:
- Player's PUUID index in `metadata.participants` matches their index in `info.participants`
- `gameDuration` is in seconds
- Timestamps are in milliseconds (epoch)

---

### League-v4 [Platform]

**Purpose**: Retrieve ranked league information for summoners.

#### Get League Entries by Summoner

```
GET /lol/league/v4/entries/by-summoner/{encryptedSummonerId}
Host: {platform}.api.riotgames.com
```

**Path Parameters:**
- `encryptedSummonerId` (string): Encrypted summoner ID from Summoner-v4

**Example Request:**
```bash
GET /lol/league/v4/entries/by-summoner/encrypted_summoner_id_here
Host: eun1.api.riotgames.com
X-Riot-Token: RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**Example Response:**
```json
[
  {
    "leagueId": "league_uuid_here",
    "summonerId": "encrypted_summoner_id_here",
    "summonerName": "PlayerName",
    "queueType": "RANKED_SOLO_5x5",
    "tier": "GOLD",
    "rank": "II",
    "leaguePoints": 45,
    "wins": 120,
    "losses": 100,
    "veteran": false,
    "inactive": false,
    "freshBlood": false,
    "hotStreak": true
  },
  {
    "leagueId": "league_uuid_here_2",
    "summonerId": "encrypted_summoner_id_here",
    "summonerName": "PlayerName",
    "queueType": "RANKED_FLEX_SR",
    "tier": "PLATINUM",
    "rank": "IV",
    "leaguePoints": 12,
    "wins": 50,
    "losses": 45,
    "veteran": false,
    "inactive": false,
    "freshBlood": false,
    "hotStreak": false
  }
]
```

**Important**:
- Returns **array** of queue types (Solo/Duo, Flex, etc.)
- Empty array `[]` if player is unranked or hasn't finished placements
- Can be empty after rank resets
- `miniSeries` field present only when in promotional series

**Queue Types:**
- `RANKED_SOLO_5x5`: Ranked Solo/Duo queue
- `RANKED_FLEX_SR`: Ranked Flex 5v5 queue
- `RANKED_FLEX_TT`: Ranked Flex 3v3 queue (deprecated)

**Tiers:**
- `IRON`, `BRONZE`, `SILVER`, `GOLD`, `PLATINUM`, `EMERALD`, `DIAMOND`, `MASTER`, `GRANDMASTER`, `CHALLENGER`

**Ranks (within tier):**
- `I`, `II`, `III`, `IV` (I is highest, IV is lowest)
- Not applicable for MASTER, GRANDMASTER, CHALLENGER tiers

---

### Spectator-v4 [Platform]

**Purpose**: Retrieve live game information.

#### Get Active Game by Summoner

```
GET /lol/spectator/v4/active-games/by-summoner/{encryptedSummonerId}
Host: {platform}.api.riotgames.com
```

**Path Parameters:**
- `encryptedSummonerId` (string): Encrypted summoner ID from Summoner-v4

**Example Request:**
```bash
GET /lol/spectator/v4/active-games/by-summoner/encrypted_summoner_id_here
Host: eun1.api.riotgames.com
X-Riot-Token: RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**Example Response (Summoner in game):**
```json
{
  "gameId": 6234567890,
  "mapId": 11,
  "gameMode": "CLASSIC",
  "gameType": "MATCHED_GAME",
  "gameQueueConfigId": 420,
  "participants": [
    {
      "championId": 157,
      "summonerName": "PlayerName",
      "summonerId": "encrypted_summoner_id",
      "teamId": 100,
      "spell1Id": 4,
      "spell2Id": 14,
      "profileIconId": 4568,
      "bot": false,
      "perks": {}
    }
  ],
  "observers": {
    "encryptionKey": "encryption_key_here"
  },
  "platformId": "EUN1",
  "bannedChampions": [],
  "gameStartTime": 1640995200000,
  "gameLength": 350
}
```

**Example Response (Summoner not in game):**
```json
{
  "status": {
    "status_code": 404,
    "message": "Data not found - summoner is not in an active game"
  }
}
```

**Important**:
- Returns 404 if summoner is not currently in a game
- `gameLength` is in seconds since game start
- `gameStartTime` is epoch timestamp in milliseconds

---

## Data Models

### AccountDTO

```typescript
{
  puuid: string;          // Player Universally Unique Identifier (globally unique)
  gameName: string;       // In-game name (before #)
  tagLine: string;        // Tag line (after #)
}
```

**Key Points:**
- PUUID is globally unique and doesn't change with region transfers
- Recommended as primary player identifier
- `gameName` + `tagLine` form the Riot ID (e.g., "smile#6578")

---

### SummonerDTO

```typescript
{
  id: string;                  // Encrypted summoner ID (platform-specific)
  accountId: string;           // Encrypted account ID (deprecated)
  puuid: string;               // Player UUID (same as AccountDTO.puuid)
  name: string;                // Summoner name (STALE since Nov 2023)
  profileIconId: number;       // Profile icon ID
  revisionDate: number;        // Date summoner was last modified (epoch ms)
  summonerLevel: number;       // Summoner level
}
```

**Key Points:**
- `id` (encrypted summoner ID) needed for League-v4 and Spectator-v4
- `name` field contains **stale data** - use Account-v1 for current Riot ID
- `revisionDate` is last modified timestamp in milliseconds
- `accountId` is deprecated, use PUUID instead

---

### MatchDTO

```typescript
{
  metadata: {
    matchId: string;              // Match identifier (e.g., "EUW1_6234567890")
    dataVersion: string;          // Data schema version
    participants: string[];       // Array of PUUIDs (10 players)
  };
  info: {
    gameCreation: number;         // Epoch timestamp (ms) when game was created
    gameDuration: number;         // Game duration in seconds
    gameStartTimestamp: number;   // Epoch timestamp (ms) when game started
    gameEndTimestamp: number;     // Epoch timestamp (ms) when game ended
    gameId: number;               // Game ID
    gameMode: string;             // Game mode (e.g., "CLASSIC", "ARAM")
    gameName: string;             // Game name
    gameType: string;             // Game type (e.g., "MATCHED_GAME")
    gameVersion: string;          // Game version (e.g., "12.1.123.4567")
    mapId: number;                // Map ID (11 = Summoner's Rift)
    platformId: string;           // Platform (e.g., "EUW1")
    queueId: number;              // Queue ID (420 = Ranked Solo, 440 = Ranked Flex)
    tournamentCode: string;       // Tournament code (empty if not tournament)
    participants: ParticipantDTO[]; // Array of participant data (10 players)
    teams: TeamDTO[];             // Array of team data (2 teams)
  };
}
```

**Important**:
- `metadata.participants` index matches `info.participants` index
- `gameDuration` is in **seconds**
- All timestamps are in **milliseconds**
- Queue ID 420 = Ranked Solo/Duo, 440 = Ranked Flex

---

### ParticipantDTO

```typescript
{
  puuid: string;                  // Player UUID
  summonerName: string;           // Summoner name (may be stale)
  summonerId: string;             // Encrypted summoner ID
  championName: string;           // Champion name (e.g., "Yasuo")
  championId: number;             // Champion ID
  teamId: number;                 // Team ID (100 = blue, 200 = red)
  teamPosition: string;           // Position (e.g., "MIDDLE", "JUNGLE", "TOP", "BOTTOM", "UTILITY")
  individualPosition: string;     // Individual position (may differ from teamPosition)
  win: boolean;                   // True if won
  kills: number;                  // Total kills
  deaths: number;                 // Total deaths
  assists: number;                // Total assists
  champLevel: number;             // Final champion level
  goldEarned: number;             // Total gold earned
  totalMinionsKilled: number;     // CS from minions
  neutralMinionsKilled: number;   // CS from jungle monsters
  visionScore: number;            // Vision score
  challenges: object;             // Challenges data (dynamic)
  perks: object;                  // Runes/perks data
  // ... many more fields available
}
```

**Key Points:**
- `teamId`: 100 (blue side), 200 (red side)
- Positions: `TOP`, `JUNGLE`, `MIDDLE`, `BOTTOM`, `UTILITY`
- Total CS = `totalMinionsKilled` + `neutralMinionsKilled`
- `challenges` and `perks` contain nested objects with detailed stats

---

### LeagueEntryDTO

```typescript
{
  leagueId: string;        // League UUID
  summonerId: string;      // Encrypted summoner ID
  summonerName: string;    // Summoner name
  queueType: string;       // Queue type (e.g., "RANKED_SOLO_5x5")
  tier: string;            // Tier (e.g., "GOLD", "PLATINUM")
  rank: string;            // Division (e.g., "I", "II", "III", "IV")
  leaguePoints: number;    // League points (0-100)
  wins: number;            // Total wins
  losses: number;          // Total losses
  veteran: boolean;        // Veteran status
  inactive: boolean;       // Inactive status
  freshBlood: boolean;     // New to tier
  hotStreak: boolean;      // Currently on hot streak
  miniSeries?: {           // Only present during promotional series
    target: number;        // Games needed to win (e.g., 3 for best of 5)
    wins: number;          // Current wins in series
    losses: number;        // Current losses in series
    progress: string;      // Series progress (e.g., "WLNNN")
  };
}
```

**Key Points:**
- Returned as **array** - player can have multiple queue types
- Empty array if unranked or no placements completed
- `miniSeries` only present when in promotional series (e.g., Gold II → Gold I)
- `rank` not applicable for MASTER, GRANDMASTER, CHALLENGER tiers

---

### TeamDTO

```typescript
{
  teamId: number;          // Team ID (100 = blue, 200 = red)
  win: boolean;            // True if won
  bans: Array<{            // Champion bans
    championId: number;    // Banned champion ID
    pickTurn: number;      // Ban order
  }>;
  objectives: {            // Team objectives
    baron: { first: boolean; kills: number };
    champion: { first: boolean; kills: number };
    dragon: { first: boolean; kills: number };
    inhibitor: { first: boolean; kills: number };
    riftHerald: { first: boolean; kills: number };
    tower: { first: boolean; kills: number };
  };
}
```

---

## Error Handling

### Common HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | OK | Success |
| 400 | Bad Request | Check request parameters |
| 401 | Unauthorized | Check API key validity |
| 403 | Forbidden | API key doesn't have access (e.g., dev key on deprecated endpoint) |
| 404 | Data Not Found | Resource doesn't exist (e.g., player not found, not in active game) |
| 429 | Rate Limit Exceeded | Respect `Retry-After` header, implement backoff |
| 500 | Internal Server Error | Riot API issue, retry with exponential backoff |
| 502 | Bad Gateway | Service temporarily unavailable |
| 503 | Service Unavailable | Service temporarily down, retry later |

### Error Response Format

```json
{
  "status": {
    "status_code": 404,
    "message": "Data not found - summoner not found"
  }
}
```

### Handling Specific Errors

**403 Forbidden on Summoner-v4 by-name:**
- Endpoint is deprecated
- Development keys may not have access
- **Solution**: Use Account-v1 `by-riot-id` to get PUUID, then Summoner-v4 `by-puuid`

**404 on Active Game:**
- Player is not currently in a game
- **Normal behavior** - handle gracefully

**429 Rate Limit:**
- Check `Retry-After` header for wait duration
- Implement exponential backoff
- Consider request queuing and throttling

**Empty Array from League Entries:**
- Player is unranked or hasn't completed placements
- **Normal behavior** - display as "Unranked"

---

## Best Practices

### 1. Use PUUID as Primary Identifier

**Why:**
- PUUIDs are globally unique and persistent across region transfers
- Summoner names are deprecated and contain stale data
- Riot is transitioning to Riot ID system

**Implementation:**
```
User Input: "smile#6578"
  ↓
Account-v1: GET /riot/account/v1/accounts/by-riot-id/smile/6578
  ↓
Store PUUID: "jUr1OkZKAS4AW6amrpxOmfYin3w9P-jiVuI7UtNmyrJRL9Z5B0R_Qzs6h7pEwCThABtBODsoyhcDbQ"
  ↓
All future lookups: Use PUUID
```

### 2. Implement Robust Caching

**What to Cache:**
- **Account/Summoner data**: TTL 24 hours (rarely changes)
- **Match data**: TTL indefinitely (matches don't change after completion)
- **League entries**: TTL 1-6 hours (changes as players play ranked)
- **Active game data**: TTL 30-60 seconds (live game state)

**Cache Key Strategy:**
```
account:{puuid}
summoner:{platform}:{puuid}
match:{region}:{matchId}
matches:{region}:{puuid}:{start}:{count}
league:{platform}:{summonerId}
```

### 3. Respect Rate Limits

**Implementation Strategies:**

**Request Queue:**
```python
# Maintain request queue per region
queue = {
  "europe": RequestQueue(rate_limit=20, window=1.0),
  "americas": RequestQueue(rate_limit=20, window=1.0)
}

# Automatic throttling
await queue["europe"].add_request(lambda: api_call())
```

**Exponential Backoff on 429:**
```python
async def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except RateLimitError as e:
            wait_time = e.retry_after or (2 ** attempt)
            await asyncio.sleep(wait_time)
    raise MaxRetriesExceeded()
```

### 4. Handle Errors Gracefully

**User-Facing Messages:**
- `404 on Account`: "Player not found. Check spelling and tagline."
- `404 on Active Game`: "Player is not currently in a game."
- `429 Rate Limit`: "Too many requests. Please try again in a moment."
- `5xx Errors`: "Riot API is experiencing issues. Please try again later."

**Logging:**
```python
logger.error(
    "API request failed",
    extra={
        "endpoint": endpoint,
        "status_code": response.status,
        "error": response.text,
        "region": region,
        "retry_after": response.headers.get("Retry-After")
    }
)
```

### 5. Batch Operations Efficiently

**Match History Fetching:**
```python
# Get match IDs (1 request)
match_ids = await get_match_ids(puuid, count=20)

# Batch requests with rate limiting
matches = []
for match_id in match_ids:
    match = await get_match(match_id)  # Check cache first
    matches.append(match)
```

**Don't:**
- Fetch all 100 matches at once without need
- Make parallel requests without rate limiting

**Do:**
- Fetch incrementally (20-50 at a time)
- Implement request throttling
- Cache aggressively

### 6. Regional Routing Best Practices

**Correct Routing:**
```python
# Account lookup: Use regional routing
account = await get_account_by_riot_id("smile", "6578", region="europe")

# Summoner data: Use platform routing
summoner = await get_summoner_by_puuid(puuid, platform="eun1")

# Match history: Use regional routing
matches = await get_match_ids(puuid, region="europe")

# Ranked info: Use platform routing
league = await get_league_entries(summoner_id, platform="eun1")
```

**Platform to Region Mapping:**
```python
PLATFORM_TO_REGION = {
    "eun1": "europe", "euw1": "europe", "tr1": "europe", "ru": "europe",
    "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas",
    "kr": "asia", "jp1": "asia",
    "oc1": "sea", "ph2": "sea", "sg2": "sea", "th2": "sea", "tw2": "sea", "vn2": "sea"
}
```

### 7. Data Consistency

**Stale Data Awareness:**
- `SummonerDTO.name` is stale as of Nov 2023 - don't display to users
- Always fetch fresh Riot ID from Account-v1 when displaying player names
- Cache invalidation after profile updates

**PUUID Consistency:**
- PUUIDs in `MatchDTO.metadata.participants` match index in `MatchDTO.info.participants`
- Use PUUID to correlate data across endpoints

### 8. Queue ID Reference

Common queue IDs used in filtering:

| Queue ID | Description |
|----------|-------------|
| 0 | Custom games |
| 400 | Normal Draft Pick |
| 420 | Ranked Solo/Duo |
| 430 | Normal Blind Pick |
| 440 | Ranked Flex |
| 450 | ARAM |
| 700 | Clash |
| 720 | ARAM Clash |
| 830 | Co-op vs AI Intro |
| 840 | Co-op vs AI Beginner |
| 850 | Co-op vs AI Intermediate |

### 9. Development Key Management

**Daily Rotation:**
```bash
# Development keys expire every 24 hours
# Automate key rotation or implement alerts

# Environment variable update
export RIOT_API_KEY="RGAPI-new-key-here"

# Application restart or hot reload
docker-compose restart backend
```

**Security:**
- Never commit API keys to version control
- Use environment variables
- Rotate keys if accidentally exposed
- Monitor for unauthorized usage

### 10. Error Recovery Patterns

**Circuit Breaker:**
```python
# Stop making requests after consecutive failures
if consecutive_failures > 5:
    circuit_breaker.open()
    raise ServiceUnavailableError("Riot API circuit breaker open")
```

**Graceful Degradation:**
```python
try:
    live_data = await fetch_from_riot_api()
except APIError:
    # Fall back to cached data
    cached_data = await fetch_from_cache()
    return cached_data or default_response
```

---

## Additional Resources

- **Official Documentation**: https://developer.riotgames.com/docs/lol
- **API Reference**: https://developer.riotgames.com/apis
- **Developer Portal**: https://developer.riotgames.com/
- **API Status**: Check Riot API status page for service incidents
- **Community Libraries**: Explore community-maintained API wrappers

---

## Document Version

- **Last Updated**: 2025-10-05
- **API Version**: Riot Games API (Latest)
- **Maintainer**: Project Documentation

For questions or updates, refer to the official Riot Developer Portal.
