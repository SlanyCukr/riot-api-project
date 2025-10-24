# Backend Architecture Diagrams

This document contains comprehensive diagrams showing how the backend system works together.

## 1. High-Level Architecture

```mermaid
---
title: Riot API Project - Backend Architecture
config:
  theme: default
---
graph TB
    subgraph "External Services"
        RIOT[Riot Games API]
    end

    subgraph "FastAPI Backend"
        API[API Endpoints<br/>Players, Matches, Detection]
        SVC[Services Layer<br/>Business Logic]
        ALG[Algorithms<br/>Player Analysis]
        RIOT_CLIENT[Riot API Client<br/>Rate Limiting & Caching]

        API --> SVC
        SVC --> ALG
        SVC --> RIOT_CLIENT
    end

    subgraph "Data Layer"
        DB[(PostgreSQL Database<br/>Players, Matches, Ranks)]
    end

    CLIENT[Frontend/API Consumer] --> API
    RIOT_CLIENT <--> RIOT
    SVC --> DB
    ALG --> DB

    style RIOT fill:#DC3545,stroke:#333,color:#fff
    style CLIENT fill:#0D6EFD,stroke:#333,color:#fff
    style DB fill:#198754,stroke:#333,color:#fff
    style API fill:#6C757D,stroke:#333,color:#fff
    style SVC fill:#6C757D,stroke:#333,color:#fff
```

---

## 2. Component Architecture

```mermaid
---
title: Backend Components & Responsibilities
---
graph LR
    subgraph "API Layer<br/>(app/api/)"
        PLAYERS_API[players.py<br/>Player endpoints]
        MATCHES_API[matches.py<br/>Match endpoints]
        DETECT_API[detection.py<br/>Detection endpoints]
    end

    subgraph "Services Layer<br/>(app/services/)"
        PLAYER_SVC[PlayerService<br/>Player operations]
        MATCH_SVC[MatchService<br/>Match operations]
        DETECT_SVC[DetectionService<br/>Player analysis]
        STATS_SVC[StatsService<br/>Statistics]
    end

    subgraph "Riot API Integration<br/>(app/riot_api/)"
        DATA_MGR[RiotDataManager<br/>Database-first data access]
        CLIENT[RiotApiClient<br/>HTTP requests]
        RATE_LIMIT[RateLimiter<br/>Rate limiting]
    end

    subgraph "Detection Algorithms<br/>(app/algorithms/)"
        WIN_RATE[WinRateAnalyzer<br/>Win rate analysis]
        RANK_PROG[RankProgressionAnalyzer<br/>Rank progression]
        PERF[PerformanceAnalyzer<br/>Performance patterns]
    end

    PLAYERS_API --> PLAYER_SVC
    MATCHES_API --> MATCH_SVC
    DETECT_API --> DETECT_SVC

    PLAYER_SVC --> DATA_MGR
    MATCH_SVC --> DATA_MGR
    DETECT_SVC --> WIN_RATE
    DETECT_SVC --> RANK_PROG
    DETECT_SVC --> PERF

    DATA_MGR --> CLIENT
    CLIENT --> RATE_LIMIT

    style PLAYERS_API fill:#0D6EFD,stroke:#333,color:#fff
    style MATCHES_API fill:#0D6EFD,stroke:#333,color:#fff
    style DETECT_API fill:#0D6EFD,stroke:#333,color:#fff
    style PLAYER_SVC fill:#6C757D,stroke:#333,color:#fff
    style MATCH_SVC fill:#6C757D,stroke:#333,color:#fff
    style DETECT_SVC fill:#6C757D,stroke:#333,color:#fff
    style DATA_MGR fill:#17A2B8,stroke:#333,color:#fff
    style CLIENT fill:#17A2B8,stroke:#333,color:#fff
    style WIN_RATE fill:#28A745,stroke:#333,color:#fff
    style RANK_PROG fill:#28A745,stroke:#333,color:#fff
    style PERF fill:#28A745,stroke:#333,color:#fff
```

---

## 3. Player Search Flow

```mermaid
---
title: Player Search Request Flow
---
sequenceDiagram
    actor User
    participant API as Players API
    participant Service as PlayerService
    participant DataMgr as RiotDataManager
    participant Client as RiotApiClient
    participant Riot as Riot API
    participant DB as PostgreSQL

    User->>API: GET /players/search?riot_id=Player#TAG
    API->>Service: get_player_by_riot_id()

    Service->>DataMgr: get_player_by_riot_id()

    DataMgr->>DB: Check if player exists in DB
    alt Player in DB
        DB-->>DataMgr: Return player from DB
        DataMgr-->>Service: Player data
    else Player not in DB
        DataMgr->>Client: Fetch from Riot API
        Client->>Client: Check rate limits

        alt Rate limit OK
            Client->>Riot: Account v1 API (Riot ID → PUUID)
            Riot-->>Client: Account data + PUUID

            Client->>Riot: Summoner v4 API (PUUID)
            Riot-->>Client: Summoner data
            Client-->>DataMgr: Combined player data

            DataMgr->>DB: Upsert player record
            DB-->>DataMgr: Stored player
            DataMgr-->>Service: Player data
        else Rate limited
            Client-->>DataMgr: None (rate limited)
            DataMgr-->>Service: None
            Service-->>API: 429 Rate Limited
            API-->>User: 429 Try again later
        end
    end

    Service-->>API: PlayerResponse
    API-->>User: 200 OK + Player JSON

    Note over Client,Riot: Rate limiting: 20 req/sec, 100 req/2min
    Note over DB: PostgreSQL is the single cache layer
```

---

## 4. Player Analysis Flow

```mermaid
---
title: Player Analysis Flow
---
sequenceDiagram
    actor User
    participant API as Detection API
    participant Service as DetectionService
    participant DB as Database
    participant WinRate as WinRateAnalyzer
    participant Rank as RankProgressionAnalyzer
    participant Perf as PerformanceAnalyzer

    User->>API: POST /detection/analyze<br/>{puuid, min_games: 30}
    API->>Service: analyze_player(puuid)

    Service->>DB: Check recent analysis (24h)
    alt Recent analysis exists
        DB-->>Service: Return cached result
        Service-->>API: DetectionResponse (cached)
    else No recent analysis
        Service->>DB: Get player data
        DB-->>Service: Player info

        Service->>DB: Get recent matches<br/>(last 30 games)
        DB-->>Service: Match list + stats

        par Analyze Win Rate
            Service->>WinRate: analyze(matches)
            WinRate->>WinRate: Calculate win rate<br/>≥65% = suspicious
            WinRate-->>Service: WinRateFactor<br/>(score, threshold)
        and Analyze Rank Progression
            Service->>Rank: analyze(puuid)
            Rank->>DB: Get rank history
            DB-->>Rank: Rank progression data
            Rank->>Rank: Calculate tier jumps<br/>Rapid climb = suspicious
            Rank-->>Service: RankFactor<br/>(score, threshold)
        and Analyze Performance
            Service->>Perf: analyze(matches)
            Perf->>Perf: KDA consistency<br/>CS patterns<br/>Damage patterns
            Perf-->>Service: PerfFactor<br/>(score, threshold)
        end

        Service->>Service: Calculate weighted score<br/>Win rate: 35%<br/>Rank: 25%<br/>Performance: 20%<br/>Account level: 15%<br/>KDA: 5%

        Service->>Service: Determine confidence<br/>High: ≥0.8<br/>Medium: ≥0.6<br/>Low: ≥0.4

        Service->>DB: Store detection result
        DB-->>Service: Saved detection

        Service-->>API: DetectionResponse<br/>(is_smurf, score, factors)
    end

    API-->>User: 200 OK + Detection JSON

    Note over Service: Multi-factor analysis<br/>combines 5 detection signals
    Note over DB: Results cached for 24h
```

---

## 5. Rate Limiting & Database Strategy

```mermaid
---
title: Rate Limiting & Database-First Flow
---
flowchart TD
    START([API Request]) --> CHECK_DB{Check<br/>Database?}

    CHECK_DB -->|Found| RETURN_DB[Return from Database]
    CHECK_DB -->|Not Found| CHECK_LIMIT{Check<br/>Rate Limit}

    CHECK_LIMIT -->|Under Limit| MAKE_REQUEST[Make Riot API Request]
    CHECK_LIMIT -->|At Limit| RETURN_NONE[Return None/<br/>Raise RateLimitError]

    MAKE_REQUEST --> REQUEST_SUCCESS{Request<br/>Successful?}

    REQUEST_SUCCESS -->|200 OK| STORE_DB[Store in Database]
    REQUEST_SUCCESS -->|429 Rate Limit| LOG_LIMIT[Log Rate Limit Event]
    REQUEST_SUCCESS -->|Other Error| RETRY{Retry<br/>Count < Max?}

    LOG_LIMIT --> BACKOFF[Exponential Backoff]
    BACKOFF --> MAKE_REQUEST

    RETRY -->|Yes| BACKOFF
    RETRY -->|No| ERROR[Throw Error]

    STORE_DB --> RETURN_DATA[Return Data]

    RETURN_DB --> END([Response])
    RETURN_DATA --> END
    RETURN_NONE --> END
    ERROR --> END

    style CHECK_DB fill:#198754,stroke:#333,color:#fff
    style STORE_DB fill:#198754,stroke:#333,color:#fff
    style CHECK_LIMIT fill:#DC3545,stroke:#333,color:#fff
    style MAKE_REQUEST fill:#0D6EFD,stroke:#333,color:#fff
    style RETURN_NONE fill:#FFC107,stroke:#333,color:#000
```

---

## 6. Data Flow Architecture

```mermaid
---
title: Data Flow - From Riot API to Database
---
graph LR
    subgraph "1. Request"
        USER[User Request]
    end

    subgraph "2. API Layer"
        ENDPOINT[FastAPI Endpoint]
    end

    subgraph "3. Service Layer"
        SERVICE[Service<br/>Business Logic]
    end

    subgraph "4. Data Management"
        DATA_MGR[RiotDataManager]
        TRANSFORM[Data Transformer]
    end

    subgraph "5. External API"
        RATE_LIMIT[Rate Limiter<br/>20/sec, 100/2min]
        CLIENT[HTTP Client]
        RIOT_API[Riot Games API]
    end

    subgraph "6. Persistence"
        DB_CHECK{In DB?}
        UPSERT[Upsert Player/Match]
        DB[(PostgreSQL)]
    end

    USER --> ENDPOINT
    ENDPOINT --> SERVICE
    SERVICE --> DATA_MGR

    DATA_MGR --> DB_CHECK
    DB_CHECK -->|Yes| SERVICE
    DB_CHECK -->|No| RATE_LIMIT

    RATE_LIMIT -->|OK| CLIENT
    RATE_LIMIT -->|Limited| SERVICE

    CLIENT --> RIOT_API
    RIOT_API --> CLIENT
    CLIENT --> TRANSFORM

    TRANSFORM --> UPSERT
    UPSERT --> DB
    DB --> SERVICE
    SERVICE --> ENDPOINT
    ENDPOINT --> USER

    style USER fill:#0D6EFD,stroke:#333,color:#fff
    style RATE_LIMIT fill:#DC3545,stroke:#333,color:#fff
    style DB fill:#198754,stroke:#333,color:#fff
    style RIOT_API fill:#DC3545,stroke:#333,color:#fff
```

## 8. Player Analysis Algorithm

```mermaid
---
title: Player Analysis - Multi-Factor Analysis
---
flowchart TD
    START([Analyze Player]) --> GET_DATA[Get Player Data<br/>+ Last 30 Matches]

    GET_DATA --> PARALLEL{Parallel Analysis}

    PARALLEL --> FACTOR1[Win Rate Analysis<br/>Weight: 35%]
    PARALLEL --> FACTOR2[Rank Progression<br/>Weight: 25%]
    PARALLEL --> FACTOR3[Performance Consistency<br/>Weight: 20%]
    PARALLEL --> FACTOR4[Account Level<br/>Weight: 15%]
    PARALLEL --> FACTOR5[KDA Analysis<br/>Weight: 5%]

    FACTOR1 --> CALC1{Win Rate<br/>≥ 65%?}
    CALC1 -->|Yes| SCORE1[Score: High]
    CALC1 -->|No| SCORE1_LOW[Score: Low]

    FACTOR2 --> CALC2{Rapid Rank<br/>Progression?}
    CALC2 -->|Yes| SCORE2[Score: High]
    CALC2 -->|No| SCORE2_LOW[Score: Low]

    FACTOR3 --> CALC3{Consistent<br/>High Performance?}
    CALC3 -->|Yes| SCORE3[Score: High]
    CALC3 -->|No| SCORE3_LOW[Score: Low]

    FACTOR4 --> CALC4{Account Level<br/>≤ 50?}
    CALC4 -->|Yes| SCORE4[Score: High]
    CALC4 -->|No| SCORE4_LOW[Score: Low]

    FACTOR5 --> CALC5{KDA<br/>≥ 3.5?}
    CALC5 -->|Yes| SCORE5[Score: High]
    CALC5 -->|No| SCORE5_LOW[Score: Low]

    SCORE1 --> WEIGHTED[Calculate Weighted Score]
    SCORE1_LOW --> WEIGHTED
    SCORE2 --> WEIGHTED
    SCORE2_LOW --> WEIGHTED
    SCORE3 --> WEIGHTED
    SCORE3_LOW --> WEIGHTED
    SCORE4 --> WEIGHTED
    SCORE4_LOW --> WEIGHTED
    SCORE5 --> WEIGHTED
    SCORE5_LOW --> WEIGHTED

    WEIGHTED --> THRESHOLD{Overall Score?}

    THRESHOLD -->|≥ 0.8| HIGH[High Confidence<br/>Smurf Detected]
    THRESHOLD -->|≥ 0.6| MEDIUM[Medium Confidence<br/>Likely Smurf]
    THRESHOLD -->|≥ 0.4| LOW[Low Confidence<br/>Possibly Smurf]
    THRESHOLD -->|< 0.4| NOT_SMURF[Not a Smurf]

    HIGH --> STORE[Store Detection Result]
    MEDIUM --> STORE
    LOW --> STORE
    NOT_SMURF --> STORE

    STORE --> END([Return Result])

    style FACTOR1 fill:#0D6EFD,stroke:#333,color:#fff
    style FACTOR2 fill:#0D6EFD,stroke:#333,color:#fff
    style FACTOR3 fill:#0D6EFD,stroke:#333,color:#fff
    style FACTOR4 fill:#0D6EFD,stroke:#333,color:#fff
    style FACTOR5 fill:#0D6EFD,stroke:#333,color:#fff
    style HIGH fill:#DC3545,stroke:#333,color:#fff
    style MEDIUM fill:#FFC107,stroke:#333,color:#000
    style LOW fill:#17A2B8,stroke:#333,color:#fff
    style NOT_SMURF fill:#28A745,stroke:#333,color:#fff
```

## Summary

These diagrams illustrate:

1. **High-Level Architecture** - Overall system structure
2. **Component Architecture** - Detailed module organization
3. **Player Search Flow** - Complete request/response cycle
4. **Player Analysis Flow** - Multi-factor analysis process
5. **Rate Limiting & Caching** - Performance optimization strategy
6. **Data Flow** - End-to-end data pipeline
7. **Database Schema** - Entity relationships and structure
8. **Detection Algorithm** - Player analysis logic
9. **API Endpoints** - RESTful API structure
10. **Deployment** - Docker container architecture

All components work together to provide efficient player search, match tracking, and intelligent player analysis with robust rate limiting and caching strategies.
