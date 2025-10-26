# Jobs Documentation

This document describes the automated background jobs that run in the Riot API project to continuously fetch and analyze player data.

## Overview

The system uses two main automated jobs:

1. **Tracked Player Updater** - Updates match history for manually tracked players
2. **Player Analyzer** - Analyzes discovered players for player analysis

Both jobs are managed by APScheduler and use the same base infrastructure for error handling, logging, and metrics collection.

---

# Player Analyzer Job

## 1. Execution Schedule

- **Automated**: Runs on configurable interval (default: 300 seconds)
- **Manual**: Manual execution available through admin interface
- **Condition**: Runs in three phases when there are players needing analysis

```mermaid
flowchart TD
    A[Job scheduler triggers<br/>or Manual execution] --> B[Phase 1: Fetch Matches]
    B --> C[Phase 2: Analyze Players]
    C --> D[Phase 3: Ban Check]
    D --> E[Job completes]

    style A fill:#9c27b0,color:#ffffff
    style B fill:#1976d2,color:#ffffff
    style C fill:#1976d2,color:#ffffff
    style D fill:#1976d2,color:#ffffff
    style E fill:#4caf50,color:#ffffff
```

## 2. Workflow

### Phase 1: Fetch Matches

```mermaid
flowchart TD
    A[Phase 1 starts] --> B[Query players table<br/>is_tracked=False AND is_active=True<br/>HAVING count matches < target_matches]
    B --> C{Players need matches?}
    C -- Yes --> D[For each player:<br/>Riot API: GET /lol/match/v5/matches/by-puuid/puuid/ids<br/>Params: count=10, queue=420]
    C -- No --> E[Phase 1 completes]
    D --> F[Fetch match details<br/>and store in database]
    F --> G[Update player's updated_at timestamp]
    G --> H{More players?}
    H -- Yes --> D
    H -- No --> E

    style A fill:#9c27b0,color:#ffffff
    style B fill:#1976d2,color:#ffffff
    style C fill:#cfa93a,color:#000000
    style D fill:#d32f2f,color:#ffffff
    style E fill:#4caf50,color:#ffffff
    style F fill:#1976d2,color:#ffffff
    style G fill:#1976d2,color:#ffffff
```

### Phase 2: Analyze Players

```mermaid
flowchart TD
    A[Phase 2 starts] --> B[Query players table<br/>is_tracked=False, is_analyzed=False, is_active=True<br/>HAVING count matches >= 20]
    B --> C{Players ready for analysis?}
    C -- Yes --> D[For each player:<br/>Call PlayerAnalysisService.analyze_player]
    C -- No --> E[Phase 2 completes]
    D --> F[Calculate 9 detection scores:<br/>win_rate, kda, account_level,<br/>rank_discrepancy, rank_progression,<br/>win_rate_trend, performance_consistency,<br/>performance_trends, role_performance]
    F --> G[Store detection result in player_analysis table]
    G --> H[UPDATE player SET is_analyzed=True<br/>and updated_at=now]
    H --> I{More players?}
    I -- Yes --> D
    I -- No --> E

    style A fill:#9c27b0,color:#ffffff
    style B fill:#1976d2,color:#ffffff
    style C fill:#cfa93a,color:#000000
    style E fill:#4caf50,color:#ffffff
    style G fill:#1976d2,color:#ffffff
    style H fill:#1976d2,color:#ffffff
```

### Phase 3: Ban Check

```mermaid
flowchart TD
    A[Phase 3 starts] --> B[Query players table joined with player_analysis<br/>WHERE is_smurf=True AND<br/>last_ban_check IS NULL OR last_ban_check < cutoff_date]
    B --> C{Smurfs need ban check?}
    C -- Yes --> D[For each player:<br/>Riot API: GET /lol/summoner/v4/summoners/by-puuid/puuid]
    C -- No --> E[Phase 3 completes]
    D --> F{Response status?}
    F -- 200 OK --> G[Player not banned<br/>UPDATE last_ban_check = now]
    F -- 404 Not Found --> H[Player likely banned<br/>UPDATE last_ban_check = now]
    F -- Other Error --> I[Log error, skip player]
    G --> J{More players?}
    H --> J
    I --> J
    J -- Yes --> D
    J -- No --> E

    style A fill:#9c27b0,color:#ffffff
    style B fill:#1976d2,color:#ffffff
    style C fill:#cfa93a,color:#000000
    style D fill:#d32f2f,color:#ffffff
    style E fill:#4caf50,color:#ffffff
    style F fill:#cfa93a,color:#000000
    style G fill:#1976d2,color:#ffffff
    style H fill:#1976d2,color:#ffffff
```

## 3. Success/Failure Handling

### Success Flow

```mermaid
flowchart TD
    A[All phases complete] --> B[Commit database transaction]
    B --> C[Log job metrics:<br/>- Players processed<br/>- Matches fetched<br/>- Players analyzed<br/>- Smurfs detected<br/>- Ban checks performed]
    C --> D[Mark job execution as SUCCESS]
    D --> E[Job completes successfully]

    style A fill:#9c27b0,color:#ffffff
    style B fill:#1976d2,color:#ffffff
    style C fill:#1976d2,color:#ffffff
    style D fill:#1976d2,color:#ffffff
    style E fill:#4caf50,color:#ffffff
```

### Failure Flow

```mermaid
flowchart TD
    A[Error occurs in phase] --> B{Error type?}
    B -- Rate Limit --> C[Log rate limit error<br/>End current phase]
    B -- API Error --> D[Log API error<br/>Continue with next player in phase]
    B -- Database Error --> E[Rollback transaction<br/>Mark phase as FAILED]
    B -- Detection Error --> F[Log detection error<br/>Continue with next player]
    C --> G[Continue to next phase]
    D --> G
    E --> H[Job marked as FAILED]
    F --> G
    G --> I{More phases?}
    I -- Yes --> J[Start next phase]
    I -- No --> K[Job completes with partial success]
    J --> G

    style A fill:#9c27b0,color:#ffffff
    style B fill:#cfa93a,color:#000000
    style H fill:#4caf50,color:#ffffff
    style K fill:#4caf50,color:#ffffff
```

## 4. Database Operations

### Tables Used and Operations

```mermaid
erDiagram
    players ||--o{ match_participants : "participates in"
    players ||--o{ player_analysis : "analyzed by"
    players ||--o{ player_ranks : "has ranks"
```

#### **players** table

- **READ**:
  - SELECT players needing matches (insufficient match count)
  - SELECT players ready for analysis (sufficient matches, not analyzed)
  - SELECT smurfs needing ban check (join with player_analysis)
- **UPDATE**:
  - SET `is_analyzed = True` after successful analysis
  - UPDATE `last_ban_check` after ban status verification
  - UPDATE `updated_at` timestamp throughout processing

#### **match_participants** table

- **READ**: COUNT matches per player for eligibility checks

#### **matches** table

- **CREATE**: INSERT new matches fetched during Phase 1

#### **player_analysis** table

- **CREATE**: INSERT new detection results with 9 scoring components

### CRUD Operations Summary

| Operation | Table                      | Purpose                             | Frequency   |
| --------- | -------------------------- | ----------------------------------- | ----------- |
| SELECT    | players                    | Get players needing matches         | Phase 1     |
| SELECT    | players                    | Get players ready for analysis      | Phase 2     |
| SELECT    | players + player_analysis | Get smurfs for ban check            | Phase 3     |
| SELECT    | match_participants         | Count player matches                | Phase 1 & 2 |
| INSERT    | matches                    | Store fetched matches               | Phase 1     |
| INSERT    | player_analysis           | Store analysis results              | Phase 2     |
| UPDATE    | players                    | Mark as analyzed, update timestamps | Phase 2 & 3 |

---

# Tracked Player Updater Job

## 1. Execution Schedule

- **Automated**: Runs on configurable interval (default: 60 seconds)
- **Manual**: Manual execution available through admin interface
- **Condition**: Only when there are players with `is_tracked = True`

```mermaid
flowchart TD
    A[Job scheduler triggers<br/>or Manual execution] --> B{Any tracked players?}
    B -- Yes --> C[Get tracked players<br/>from database]
    B -- No --> Z[Job completes - no work]
    C --> D[Process each tracked player]
    D --> E[Job completes]

    style A fill:#9c27b0,color:#ffffff
    style B fill:#cfa93a,color:#000000
    style Z fill:#4caf50,color:#ffffff
    style E fill:#4caf50,color:#ffffff
```

## 2. Workflow

```mermaid
flowchart TD
    A[Job starts] --> B[Query players table<br/>is_tracked=True AND is_active=True]
    B --> C[Get player's last_match_time<br/>from match_participants table]
    C --> D[Calculate fetch start time<br/>based on existing match count]
    D --> E[Riot API: GET /lol/match/v5/matches/by-puuid/puuid/ids<br/>Params: queue=420, startTime, count=100]
    E --> F[Filter match IDs against<br/>existing matches in matches table]
    F --> G{New matches found?}
    G -- Yes --> H[Process each new match]
    G -- No --> M[Update player rank]
    H --> I[Riot API: GET /lol/match/v5/matches/matchId]
    I --> J[Extract participant data<br/>from match response]
    J --> K[Create missing player records in players table<br/>for new participants discovered]
    K --> L[Store match in matches table<br/>and participants in match_participants table]
    L --> M
    M --> N[Riot API: GET /lol/league/v4/entries/by-puuid/puuid<br/>Get ranked stats]
    N --> O[Store rank data in player_ranks table]
    O --> P[Update player's updated_at timestamp]
    P --> Q[SUCCESS: Job completes]

    style A fill:#9c27b0,color:#ffffff
    style B fill:#1976d2,color:#ffffff
    style C fill:#1976d2,color:#ffffff
    style D fill:#1976d2,color:#ffffff
    style E fill:#d32f2f,color:#ffffff
    style F fill:#1976d2,color:#ffffff
    style G fill:#cfa93a,color:#000000
    style I fill:#d32f2f,color:#ffffff
    style J fill:#1976d2,color:#ffffff
    style K fill:#1976d2,color:#ffffff
    style L fill:#1976d2,color:#ffffff
    style N fill:#d32f2f,color:#ffffff
    style O fill:#1976d2,color:#ffffff
    style P fill:#1976d2,color:#ffffff
    style Q fill:#4caf50,color:#ffffff
```

## 3. Success/Failure Handling

### Success Flow

```mermaid
flowchart TD
    A[All players processed] --> B[Commit database transaction]
    B --> C[Log job metrics:<br/>- Players processed<br/>- Matches fetched<br/>- Players discovered<br/>- API requests made]
    C --> D[Mark job execution as SUCCESS]
    D --> E[Job completes successfully]

    style A fill:#9c27b0,color:#ffffff
    style B fill:#1976d2,color:#ffffff
    style C fill:#1976d2,color:#ffffff
    style D fill:#1976d2,color:#ffffff
    style E fill:#4caf50,color:#ffffff
```

### Failure Flow

```mermaid
flowchart TD
    A[Error occurs] --> B{Error type?}
    B -- Rate Limit --> C[Log rate limit error<br/>Wait for retry]
    B -- API Error --> D[Log API error<br/>Continue with next player]
    B -- Database Error --> E[Rollback transaction<br/>Log critical error]
    B -- Other Error --> F[Log error<br/>Continue if non-critical]
    C --> G[Job marked as FAILED]
    D --> H[Continue with next player]
    E --> G
    F --> H
    H --> I{More players?}
    I -- Yes --> J[Process next player]
    I -- No --> K[Job completes with partial success]
    J --> H

    style A fill:#9c27b0,color:#ffffff
    style B fill:#cfa93a,color:#000000
    style G fill:#4caf50,color:#ffffff
    style K fill:#4caf50,color:#ffffff
```

## 4. Database Operations

### Tables Used and Operations

```mermaid
erDiagram
    players ||--o{ match_participants : "participates in"
    matches ||--o{ match_participants : "contains"
    players ||--o{ player_ranks : "has ranks"
```

#### **players** table

- **READ**: SELECT players with `is_tracked = True` AND `is_active = True`
- **CREATE**: INSERT new player records for discovered participants (minimal data: puuid, summoner_name, platform, is_tracked=False, is_analyzed=False)
- **UPDATE**: UPDATE `updated_at` timestamp after processing each player

#### **matches** table

- **READ**: SELECT existing match IDs to avoid duplicates
- **CREATE**: INSERT new match records from Riot API data

#### **match_participants** table

- **READ**: SELECT player's match history and timestamps
- **CREATE**: INSERT participant records for each processed match

#### **player_ranks** table

- **CREATE**: INSERT new rank records when player's ranked data changes

### CRUD Operations Summary

| Operation | Table              | Purpose                      | Frequency       |
| --------- | ------------------ | ---------------------------- | --------------- |
| SELECT    | players            | Get tracked players list     | Once per job    |
| SELECT    | match_participants | Get player's last match time | Once per player |
| SELECT    | matches            | Check existing matches       | Once per player |
| INSERT    | players            | Create discovered players    | As needed       |
| INSERT    | matches            | Store new matches            | As needed       |
| INSERT    | match_participants | Store match participants     | As needed       |
| INSERT    | player_ranks       | Store rank updates           | As needed       |
| UPDATE    | players            | Update timestamps            | Once per player |

---

# Job Configuration and Monitoring

## Job Configuration Storage

Job configurations are stored in the **job_configurations** table:

- **job_type**: Enum (`TRACKED_PLAYER_UPDATER` or `PLAYER_ANALYZER`)
- **schedule**: Interval string (e.g., "60", "interval:300")
- **is_active**: Boolean flag to enable/disable jobs
- **config_json**: JSON configuration for job-specific parameters

## Job Execution Tracking

All job executions are logged to the **job_executions** table:

- **job_config_id**: Foreign key to job configuration
- **started_at / completed_at**: Execution timestamps
- **status**: Enum (`PENDING`, `RUNNING`, `SUCCESS`, `FAILED`)
- **api_requests_made**: Number of Riot API calls
- **records_created / records_updated**: Database operation counts
- **error_message**: Error details if failed
- **execution_log**: Detailed JSON log of execution metrics

## Rate Limiting and API Management

Both jobs respect Riot API rate limits:

- **Automatic retry** with exponential backoff on rate limit errors
- **Request counting** to track API usage
- **Error handling** to continue processing when individual requests fail
- **Metrics collection** for monitoring API usage patterns

---

# Important Notes

1. **Database Transactions**: Each job uses database transactions with proper rollback on errors
2. **Error Handling**: Non-critical errors (individual player failures) don't stop the entire job
3. **Rate Limits**: Jobs automatically handle Riot API rate limits with proper retry logic
4. **Idempotency**: Jobs are designed to be safe to run multiple times - they check for existing data before making changes
5. **Resource Management**: Jobs properly clean up API clients and database connections
6. **Logging**: Comprehensive logging with structured logs for debugging and monitoring
7. **Metrics**: Jobs track execution metrics for performance monitoring and optimization
