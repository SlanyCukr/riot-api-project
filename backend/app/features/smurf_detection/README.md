# Smurf Detection Feature

## Purpose

Analyzes League of Legends player accounts to detect potential smurfs (experienced players using low-level accounts). Uses multiple factors including account level, win rate, performance metrics, rank progression, and champion mastery to generate a comprehensive smurf likelihood score.

## API Endpoints

### Smurf Analysis
- `POST /api/v1/player-analysis/{puuid}` - Analyze a player account for smurf indicators
- `GET /api/v1/player-analysis/{puuid}/history` - Get historical smurf detection results
- `GET /api/v1/player-analysis/{puuid}/latest` - Get the most recent analysis

### Detection Configuration
- `GET /api/v1/player-analysis/config` - Get current detection thresholds and weights
- `PUT /api/v1/player-analysis/config` - Update detection configuration (admin only)

## Key Components

### Router (`router.py`)
FastAPI router defining smurf detection endpoints. Handles analysis requests and configuration management.

### Service (`service.py`)
**SmurfDetectionService** - Core business logic for smurf detection:
- Orchestrates multiple analyzers to evaluate accounts
- Calculates weighted smurf scores
- Stores detection results in database
- Provides historical analysis tracking

### Models (`models.py`)
**SQLAlchemy Models:**
- `SmurfDetection` - Detection result entity (PUUID, overall score, factor scores, analysis timestamp)

### Schemas (`schemas.py`)
**Pydantic Schemas:**
- `SmurfDetectionRequest` - Request to analyze a player
- `SmurfDetectionResponse` - Analysis results with factor breakdown
- `FactorScore` - Individual factor score and weight
- `DetectionConfig` - Configuration for thresholds and weights

### Configuration (`config.py`)
Detection thresholds and weights for each analysis factor:
- Win rate thresholds and weights
- Account level thresholds
- Performance metric weights
- Rank progression weights
- Champion mastery weights

### Analyzers (`analyzers/`)
Modular factor analyzers:
- `base.py` - BaseAnalyzer abstract class
- `win_rate.py` - Win rate analysis
- `account_level.py` - Account age and level analysis
- `performance.py` - KDA, CS/min, damage metrics
- `rank_progression.py` - Climb speed analysis
- `champion_mastery.py` - Champion pool diversity

### Dependencies (`dependencies.py`)
- `get_smurf_detection_service()` - Dependency injection for SmurfDetectionService

## Dependencies

### Core Dependencies
- `core.database` - Database session management
- `core.riot_api` - Riot API data (via player and match services)
- `core.config` - Application settings

### Feature Dependencies
- `features.players` - Player data and rank information
- `features.matches` - Match history for performance analysis

### External Libraries
- SQLAlchemy - ORM for database operations
- Pydantic - Data validation and serialization
- FastAPI - API routing and dependency injection

## Detection Algorithm

The smurf detection system uses a multi-factor weighted scoring approach:

1. **Win Rate Analysis** (Weight: 25%)
   - Abnormally high win rates (>65% over 20+ games)
   - Consistent wins across different champions

2. **Account Level Analysis** (Weight: 20%)
   - New accounts with high performance
   - Account age vs. skill level mismatch

3. **Performance Metrics** (Weight: 25%)
   - High KDA ratios (>4.0)
   - Exceptional CS/min for rank (>7.5 in Silver/Gold)
   - High damage output compared to rank average

4. **Rank Progression** (Weight: 15%)
   - Rapid climb through ranks
   - High win streak frequency
   - Skipping divisions

5. **Champion Mastery** (Weight: 15%)
   - Small champion pool with high mastery
   - Dominant performance on specific champions

**Final Score Calculation:**
```
smurf_score = Σ(factor_score × factor_weight)
```

Scores range from 0-100:
- 0-30: Unlikely to be a smurf
- 30-60: Possible smurf indicators
- 60-100: High likelihood of smurf account

## Usage Examples

### Analyzing a Player Account

```python
from app.features.smurf_detection.dependencies import get_smurf_detection_service

async def analyze_player(
    puuid: str,
    detection_service = Depends(get_smurf_detection_service)
):
    result = await detection_service.analyze_player(puuid)
    print(f"Smurf Score: {result.overall_score}")
    for factor in result.factors:
        print(f"{factor.name}: {factor.score} (weight: {factor.weight})")
```

### Creating a Custom Analyzer

```python
from app.features.smurf_detection.analyzers.base import BaseAnalyzer

class CustomAnalyzer(BaseAnalyzer):
    async def analyze(self, puuid: str) -> float:
        # Your custom analysis logic
        score = 0.0
        # Calculate score based on your criteria
        return min(max(score, 0.0), 100.0)  # Clamp to 0-100

    @property
    def factor_name(self) -> str:
        return "custom_factor"

    @property
    def weight(self) -> float:
        return 0.10  # 10% weight
```

### Updating Detection Configuration

```python
from app.features.smurf_detection.config import DetectionConfig

config = DetectionConfig(
    win_rate_threshold=0.65,
    win_rate_weight=0.25,
    account_level_threshold=50,
    performance_weight=0.25,
    # ... other thresholds
)
```

## Related Features

- **Players** - Requires player data and rank information
- **Matches** - Analyzes match performance metrics
- **Jobs** - Background jobs can run periodic smurf analysis on tracked players
- **Matchmaking Analysis** - Smurf detection feeds into matchmaking fairness evaluation

## Future Enhancements

- Machine learning model integration
- Historical trend analysis
- Comparison with known smurf patterns
- Integration with Riot's smurf detection systems
- Real-time analysis as matches complete
