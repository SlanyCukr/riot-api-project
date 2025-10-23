# Matchmaking Analysis Feature

## Purpose

Evaluates the fairness and balance of League of Legends matchmaking by analyzing team compositions, rank distributions, and performance metrics. Provides insights into whether matches are balanced or if certain teams have inherent advantages.

## API Endpoints

### Matchmaking Analysis

- `GET /api/v1/matchmaking-analysis/{puuid}` - Analyze matchmaking fairness for a player
- `GET /api/v1/matchmaking-analysis/{match_id}` - Analyze fairness for a specific match
- `POST /api/v1/matchmaking-analysis/batch` - Analyze multiple matches in batch

### Fairness Metrics

- `GET /api/v1/matchmaking-analysis/{puuid}/trends` - Get matchmaking fairness trends over time
- `GET /api/v1/matchmaking-analysis/{puuid}/summary` - Get aggregated fairness summary

## Key Components

### Router (`router.py`)

FastAPI router defining matchmaking analysis endpoints. Handles analysis requests and result retrieval.

### Service (`service.py`)

**MatchmakingAnalysisService** - Core business logic for fairness evaluation:

- Team composition analysis
- Rank distribution comparison
- Historical performance evaluation
- Fairness score calculation
- Trend analysis over multiple matches

### Models (`models.py`)

**SQLAlchemy Models:**

- `MatchmakingAnalysis` - Analysis result entity (match ID, PUUID, fairness score, team metrics, timestamp)

### Schemas (`schemas.py`)

**Pydantic Schemas:**

- `MatchmakingAnalysisRequest` - Request to analyze matchmaking
- `MatchmakingAnalysisResponse` - Analysis results with fairness metrics
- `TeamMetrics` - Team-level statistics and composition
- `FairnessScore` - Overall fairness score with breakdown

### Dependencies (`dependencies.py`)

- `get_matchmaking_analysis_service()` - Dependency injection for MatchmakingAnalysisService

## Dependencies

### Core Dependencies

- `core.database` - Database session management
- `core.config` - Application settings

### Feature Dependencies

- `features.players` - Player rank and account information
- `features.matches` - Match data and participant details

### External Libraries

- SQLAlchemy - ORM for database operations
- Pydantic - Data validation and serialization
- FastAPI - API routing and dependency injection

## Analysis Methodology

The matchmaking analysis evaluates several factors:

### 1. Rank Distribution (40% weight)

- Average rank difference between teams
- Rank spread within each team
- Presence of outliers (players significantly above/below team average)

### 2. Historical Performance (30% weight)

- Recent win rates for each team
- Average KDA for each team
- Performance trends (improving vs. declining players)

### 3. Team Composition (20% weight)

- Role distribution balance
- Champion synergy (basic analysis)
- Experience with champions played

### 4. Account Factors (10% weight)

- Account age distribution
- Smurf likelihood impact
- Queue type experience

**Fairness Score Calculation:**

```
fairness_score = 100 - Σ(deviation × weight)
```

Scores range from 0-100:

- 90-100: Excellent matchmaking (very balanced)
- 75-89: Good matchmaking (minor imbalances)
- 60-74: Fair matchmaking (noticeable imbalances)
- 0-59: Poor matchmaking (significant imbalances)

## Usage Examples

### Analyzing Player Matchmaking

```python
from app.features.matchmaking_analysis.dependencies import get_matchmaking_analysis_service

async def analyze_player_matchmaking(
    puuid: str,
    analysis_service = Depends(get_matchmaking_analysis_service)
):
    result = await analysis_service.analyze_player_matches(puuid, match_count=20)
    print(f"Average Fairness Score: {result.average_fairness}")
    print(f"Matches Analyzed: {len(result.matches)}")
    for match in result.matches:
        print(f"Match {match.match_id}: {match.fairness_score}/100")
```

### Analyzing a Specific Match

```python
async def analyze_match(
    match_id: str,
    analysis_service = Depends(get_matchmaking_analysis_service)
):
    result = await analysis_service.analyze_match(match_id)

    print(f"Fairness Score: {result.fairness_score}/100")
    print(f"Team 1 Average Rank: {result.team1_metrics.average_rank}")
    print(f"Team 2 Average Rank: {result.team2_metrics.average_rank}")
    print(f"Rank Difference: {result.rank_difference}")
```

### Batch Analysis

```python
async def batch_analyze(
    match_ids: list[str],
    analysis_service = Depends(get_matchmaking_analysis_service)
):
    results = await analysis_service.analyze_matches_batch(match_ids)

    fair_matches = [r for r in results if r.fairness_score >= 75]
    print(f"{len(fair_matches)}/{len(results)} matches were fair")
```

### Trend Analysis

```python
async def get_fairness_trends(
    puuid: str,
    analysis_service = Depends(get_matchmaking_analysis_service)
):
    trends = await analysis_service.get_fairness_trends(puuid, days=30)

    for period in trends:
        print(f"{period.date}: Avg Fairness {period.average_fairness}")
        print(f"  Matches: {period.match_count}")
        print(f"  Win Rate: {period.win_rate}%")
```

## Data Model

### MatchmakingAnalysis

- `id` (int, PK) - Auto-increment ID
- `match_id` (str, FK) - Reference to Match
- `puuid` (str) - Player analyzed
- `fairness_score` (float) - Overall fairness score (0-100)
- `rank_distribution_score` (float) - Rank balance score
- `performance_score` (float) - Historical performance score
- `composition_score` (float) - Team composition score
- `team1_average_rank` (str) - Average rank for team 1
- `team2_average_rank` (str) - Average rank for team 2
- `analysis_timestamp` (datetime) - When analysis was performed

## Interpretation Guide

### Fairness Score Ranges

**90-100: Excellent**

- Teams are very evenly matched
- Minimal rank differences
- Similar historical performance
- Balanced compositions

**75-89: Good**

- Generally balanced teams
- Minor rank variations (1-2 divisions)
- Reasonable performance parity
- Minor composition advantages

**60-74: Fair**

- Noticeable imbalances
- Rank differences of 2-3 divisions
- Performance gaps present
- Some composition mismatches

**0-59: Poor**

- Significant imbalances
- Large rank disparities
- Major performance differences
- Composition advantages

### Common Imbalance Patterns

1. **Duo Queue Impact**: Pre-made duos can create rank disparities
2. **Smurf Presence**: Smurfs significantly skew matchmaking
3. **Role Autofill**: Players on off-roles may underperform
4. **Streak Effects**: Players on win/loss streaks may have inflated/deflated MMR

## Related Features

- **Players** - Requires player rank and account data
- **Matches** - Analyzes match data and participant stats
- **Smurf Detection** - Smurf likelihood affects fairness evaluation
- **Jobs** - Background jobs can run periodic fairness analysis

## Future Enhancements

- MMR estimation (Riot doesn't expose MMR directly)
- Role assignment impact analysis
- Queue time correlation with fairness
- Historical MMR tracking
- Predictive match outcome based on fairness metrics
