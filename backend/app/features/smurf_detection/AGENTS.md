# Smurf Detection Feature

## Overview

The smurf detection feature implements a multi-factor analysis algorithm to identify likely smurf accounts (experienced players using low-level accounts). This feature has unique architecture with modular analyzers and weighted scoring.

**See `README.md` for comprehensive API documentation and component descriptions.**

## Unique Architecture

Unlike standard features, smurf detection has:

- **`analyzers/` subdirectory** - Modular factor analyzers
- **`config.py`** - Detection thresholds and weights configuration
- **Complex service layer** - Orchestrates multiple analyzers

### Directory Structure

```
smurf_detection/
├── __init__.py
├── router.py
├── service.py              # Orchestrates analyzers, calculates weighted scores
├── models.py               # SmurfDetection model
├── schemas.py
├── dependencies.py
├── config.py               # Factor weights and thresholds
├── analyzers/              # Modular factor analyzers
│   ├── __init__.py
│   ├── win_rate.py
│   ├── account_level.py
│   ├── performance.py
│   ├── rank_progression.py
│   └── ... (9 total analyzers)
├── tests/
└── README.md
```

## Detection Algorithm

### 9-Factor Analysis

Each analyzer evaluates one aspect of player behavior:

1. **Rank Discrepancy** (20% weight) - Performance vs current rank
2. **Win Rate Analysis** (18% weight) - Sustained high win rates
3. **Performance Trends** (15% weight) - KDA patterns
4. **Win Rate Trends** (10% weight) - Rapid win rate improvement
5. **Role Performance** (9% weight) - Multi-role versatility
6. **Rank Progression** (9% weight) - Fast rank climbing
7. **Account Level** (8% weight) - Low level + high performance
8. **Performance Consistency** (8% weight) - Low variance
9. **KDA Analysis** (3% weight) - Exceptional K/D/A ratios

**Weighted Score:**

```
final_score = Σ(factor_score × factor_weight)
```

**Confidence Levels:**

- **High (80%+)**: Very likely smurf
- **Medium (60-79%)**: Probable smurf
- **Low (40-59%)**: Possible smurf
- **< 40%**: Unlikely to be smurf

### How It Works

```python
# 1. Service orchestrates analyzers
service = SmurfDetectionService(riot_data_manager)
result = await service.analyze_player(puuid, platform, db)

# 2. Each analyzer evaluates its factor
# (Inside service)
for analyzer in self.analyzers:
    factor_score = await analyzer.analyze(player_data)
    factor_scores.append(factor_score)

# 3. Weighted sum produces final score
final_score = sum(score * weight for score, weight in factor_scores)

# 4. Result stored in database
detection = SmurfDetection(
    player_id=player.id,
    overall_score=final_score,
    factor_scores=factor_scores,
    confidence_level=self._calculate_confidence(final_score)
)
db.add(detection)
await db.commit()
```

## Analyzer Pattern

Each analyzer in `analyzers/` follows this interface:

```python
# analyzers/base.py (conceptual)
class BaseAnalyzer(ABC):
    """Base class for smurf detection analyzers."""

    weight: float  # Factor weight (0.0 to 1.0)

    @abstractmethod
    async def analyze(
        self,
        player: Player,
        matches: list[Match],
        rank: Rank | None,
        db: AsyncSession
    ) -> float:
        """Analyze factor and return score 0.0-1.0."""
        pass
```

Example analyzer:

```python
# analyzers/win_rate.py
class WinRateAnalyzer:
    """Analyzes win rate patterns."""

    weight = 0.18  # 18% of final score

    async def analyze(
        self,
        player: Player,
        matches: list[Match],
        rank: Rank | None,
        db: AsyncSession
    ) -> float:
        """Calculate win rate score.

        :param player: Player being analyzed
        :param matches: Recent match history
        :param rank: Current rank info
        :param db: Database session
        :returns: Score between 0.0 and 1.0
        """
        if not matches:
            return 0.0

        wins = sum(1 for m in matches if m.win)
        win_rate = wins / len(matches)

        # High sustained win rate indicates smurf
        if win_rate >= 0.70:
            return 1.0
        elif win_rate >= 0.60:
            return 0.7
        elif win_rate >= 0.55:
            return 0.4
        else:
            return 0.0
```

## Configuration Management

### Detection Config (`config.py`)

```python
from dataclasses import dataclass

@dataclass
class DetectionConfig:
    """Smurf detection configuration."""

    # Thresholds
    high_win_rate_threshold: float = 0.70
    account_level_threshold: int = 50
    high_kda_threshold: float = 3.5

    # Weights (must sum to 1.0)
    rank_discrepancy_weight: float = 0.20
    win_rate_weight: float = 0.18
    performance_weight: float = 0.15
    # ... etc

    def validate(self) -> None:
        """Ensure weights sum to 1.0."""
        total = sum([
            self.rank_discrepancy_weight,
            self.win_rate_weight,
            # ...
        ])
        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, not 1.0"
```

### Updating Configuration

Configuration can be updated via API:

```bash
curl -X PUT http://localhost:8000/api/v1/player-analysis/config \
  -H "Content-Type: application/json" \
  -d '{
    "high_win_rate_threshold": 0.75,
    "rank_discrepancy_weight": 0.25
  }'
```

## Service Layer

**`SmurfDetectionService`** orchestrates the detection process:

```python
class SmurfDetectionService:
    """Service for smurf detection operations."""

    def __init__(self, riot_data_manager: RiotDataManager):
        self.riot_data_manager = riot_data_manager
        self.config = DetectionConfig()
        self.analyzers = self._initialize_analyzers()

    async def analyze_player(
        self,
        puuid: str,
        platform: Platform,
        db: AsyncSession
    ) -> SmurfDetection:
        """Perform comprehensive smurf analysis.

        :param puuid: Player's unique ID
        :param platform: Riot platform
        :param db: Database session
        :returns: Detection result with factor breakdown
        """
        # 1. Fetch player data
        player = await self._get_player_data(puuid, platform, db)
        matches = await self._get_recent_matches(player, db)
        rank = await self._get_rank_info(player, db)

        # 2. Run all analyzers
        factor_scores = {}
        for name, analyzer in self.analyzers.items():
            score = await analyzer.analyze(player, matches, rank, db)
            factor_scores[name] = {
                "score": score,
                "weight": analyzer.weight,
                "weighted_score": score * analyzer.weight
            }

        # 3. Calculate final score
        final_score = sum(
            data["weighted_score"] for data in factor_scores.values()
        )

        # 4. Store result
        detection = SmurfDetection(
            player_id=player.id,
            overall_score=final_score,
            factor_scores=factor_scores,
            confidence_level=self._calculate_confidence(final_score),
            analysis_timestamp=datetime.utcnow()
        )
        db.add(detection)
        await db.commit()

        logger.info(
            "smurf_analysis_complete",
            puuid=puuid,
            score=final_score,
            confidence=detection.confidence_level
        )

        return detection
```

## Database Model

```python
class SmurfDetection(BaseModel):
    """Smurf detection result."""

    __tablename__ = "smurf_detections"

    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    overall_score = Column(Float, nullable=False)
    factor_scores = Column(JSON, nullable=False)  # Dict of factor results
    confidence_level = Column(String, nullable=False)  # HIGH/MEDIUM/LOW
    analysis_timestamp = Column(DateTime, nullable=False)

    # Relationships
    player = relationship("Player", back_populates="smurf_detections")
```

## Adding a New Analyzer

1. **Create analyzer file** in `analyzers/`:

   ```python
   # analyzers/new_factor.py
   class NewFactorAnalyzer:
       weight = 0.05  # 5% of final score

       async def analyze(self, player, matches, rank, db) -> float:
           # Your logic here
           return score  # 0.0 to 1.0
   ```

2. **Register in service** (`service.py`):

   ```python
   def _initialize_analyzers(self):
       return {
           "new_factor": NewFactorAnalyzer(),
           # ... other analyzers
       }
   ```

3. **Adjust weights** in `config.py` to ensure sum = 1.0

4. **Update tests** to include new factor

5. **Document** in README.md

## Testing

Smurf detection tests should verify:

- Individual analyzer logic
- Weighted score calculation
- Configuration validation
- Service orchestration

```python
@pytest.mark.asyncio
async def test_win_rate_analyzer():
    """Test win rate analyzer logic."""
    analyzer = WinRateAnalyzer()

    # High win rate player
    high_wr_matches = [Match(win=True) for _ in range(7)] + [Match(win=False) for _ in range(3)]
    score = await analyzer.analyze(player, high_wr_matches, rank, db)
    assert score >= 0.7

    # Normal win rate player
    normal_wr_matches = [Match(win=True) for _ in range(5)] + [Match(win=False) for _ in range(5)]
    score = await analyzer.analyze(player, normal_wr_matches, rank, db)
    assert score < 0.5
```

## Import Patterns

```python
# Using smurf detection from other features
from app.features.smurf_detection import SmurfDetectionService, SmurfDetection

# Internal imports within feature
from .analyzers.win_rate import WinRateAnalyzer
from .config import DetectionConfig
from .service import SmurfDetectionService
```

## See Also

- `README.md` - Comprehensive API documentation and component descriptions
- `backend/app/features/AGENTS.md` - General feature development guide
- `backend/app/core/AGENTS.md` - Core infrastructure
- `openspec/project.md` - Project context and smurf detection algorithm overview
