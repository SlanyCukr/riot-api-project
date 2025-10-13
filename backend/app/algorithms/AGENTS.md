# Smurf Detection Algorithms Guide

**WHEN TO USE THIS**: Adding/modifying smurf detection algorithms or adjusting detection thresholds.

**QUICK START**: Adding algorithm? → [Jump to Quick Recipe](#-quick-recipe-add-an-algorithm)

---

## 📁 Available Algorithms

| Algorithm | File | Detects | Confidence Thresholds |
|-----------|------|---------|----------------------|
| **Win Rate** | `win_rate.py` | Abnormally high win rates | ≥70% (high), ≥65% (medium) |
| **Rank Progression** | `rank_progression.py` | Rapid rank climbing, level/rank mismatch | Account age vs rank |
| **Performance** | `performance.py` | Consistent high performance | KDA, CS/min, damage stability |

---

## 🎯 Quick Recipe: Add an Algorithm

### 1. Create Algorithm File

**File**: `backend/app/algorithms/<name>.py`

### 2. Implement Algorithm Class

```python
# app/algorithms/champion_pool.py
from typing import List
from ..models.matches import Match
from ..models.participants import Participant
import structlog

logger = structlog.get_logger(__name__)

class ChampionPoolDetector:
    """
    Detect smurfs based on champion pool size.

    Smurfs often play limited champion pools with high mastery.
    """

    def calculate_confidence(
        self,
        matches: List[Match],
        participants: List[Participant] | None = None,
        **kwargs
    ) -> float:
        """
        Calculate smurf confidence score based on champion pool.

        Args:
            matches: List of player's matches
            participants: List of participant records (optional)
            **kwargs: Additional parameters for extensibility

        Returns:
            Confidence score between 0 and 100

        Raises:
            ValueError: If matches list is empty
        """
        if not matches:
            logger.warning("empty_matches_list")
            raise ValueError("Matches list cannot be empty")

        # Extract champion play counts
        champion_counts = self._count_champions(participants or [])

        # Calculate metrics
        unique_champions = len(champion_counts)
        total_games = len(matches)
        most_played_count = max(champion_counts.values()) if champion_counts else 0
        concentration = most_played_count / total_games if total_games > 0 else 0

        # Scoring logic
        confidence = 0.0

        # Very limited pool (< 3 champions)
        if unique_champions <= 3 and total_games >= 20:
            confidence += 40

        # High concentration (>60% on one champion)
        if concentration >= 0.6:
            confidence += 30

        # Combine with win rate on most played
        if concentration >= 0.5:
            most_played_wins = self._get_wins_on_champion(
                participants or [],
                most_played_count
            )
            win_rate = most_played_wins / most_played_count if most_played_count > 0 else 0
            if win_rate >= 0.7:
                confidence += 30

        logger.info(
            "champion_pool_analysis",
            unique_champions=unique_champions,
            most_played_count=most_played_count,
            concentration=concentration,
            confidence=confidence
        )

        return min(confidence, 100.0)  # Cap at 100

    def _count_champions(self, participants: List[Participant]) -> dict:
        """Count games per champion."""
        counts = {}
        for p in participants:
            counts[p.champion_id] = counts.get(p.champion_id, 0) + 1
        return counts

    def _get_wins_on_champion(self, participants: List[Participant], champion_id: int) -> int:
        """Count wins on specific champion."""
        return sum(1 for p in participants if p.champion_id == champion_id and p.win)
```

### 3. Register in Detection Service

```python
# app/services/detection.py
from ..algorithms.win_rate import WinRateDetector
from ..algorithms.rank_progression import RankProgressionDetector
from ..algorithms.performance import PerformanceDetector
from ..algorithms.champion_pool import ChampionPoolDetector  # Add import

class SmurfDetectionService:
    def __init__(self, db: AsyncSession, riot_data_manager: RiotDataManager):
        self.db = db
        self.data_manager = riot_data_manager

        # Initialize algorithms
        self.win_rate_detector = WinRateDetector()
        self.rank_progression_detector = RankProgressionDetector()
        self.performance_detector = PerformanceDetector()
        self.champion_pool_detector = ChampionPoolDetector()  # Add here

    async def analyze_player(self, puuid: str) -> DetectionResult:
        """Run all detection algorithms."""
        # ... fetch data ...

        # Run algorithms
        win_rate_score = self.win_rate_detector.calculate_confidence(matches)
        rank_score = self.rank_progression_detector.calculate_confidence(matches, player=player)
        performance_score = self.performance_detector.calculate_confidence(matches, participants)
        champion_score = self.champion_pool_detector.calculate_confidence(matches, participants)  # Add here

        # Combine scores (weighted average)
        overall = (
            win_rate_score * 0.3 +
            rank_score * 0.3 +
            performance_score * 0.2 +
            champion_score * 0.2  # Add to formula
        )

        return DetectionResult(
            overall_confidence=overall,
            win_rate_score=win_rate_score,
            rank_progression_score=rank_score,
            performance_score=performance_score,
            champion_pool_score=champion_score,  # Add field
            is_smurf=overall >= 70.0
        )
```

### 4. Update Database Schema (if needed)

```python
# app/models/smurf_detection.py
class SmurfDetection(Base):
    __tablename__ = "smurf_detections"

    # ... existing fields ...

    champion_pool_score = Column(Float, nullable=True)  # Add new score field
```

---

## 📊 Existing Algorithms Deep Dive

### Win Rate Detector (`win_rate.py`)

**What it detects**: Abnormally high win rates over many games

**Scoring**:
```python
# High confidence (80-100)
- Win rate ≥ 70% with 40+ games
- Win rate ≥ 75% with 30+ games

# Medium confidence (50-79)
- Win rate ≥ 65% with 30+ games
- Win rate ≥ 70% with 20+ games

# Low confidence (0-49)
- Below thresholds
```

**Usage**:
```python
detector = WinRateDetector()
confidence = detector.calculate_confidence(matches)
```

### Rank Progression Detector (`rank_progression.py`)

**What it detects**:
- Rapid rank climbing (e.g., Silver → Diamond in < 50 games)
- Account level vs rank mismatch (e.g., level 35 in Diamond)

**Factors**:
- Starting rank vs current rank
- Games played in current season
- Account level
- Division skipping patterns

**Usage**:
```python
detector = RankProgressionDetector()
confidence = detector.calculate_confidence(matches, player=player, rank=rank)
```

### Performance Detector (`performance.py`)

**What it detects**: Consistently high performance metrics

**Metrics analyzed**:
- KDA (Kill/Death/Assist ratio)
- CS per minute (creep score)
- Damage output
- Vision score
- Gold efficiency

**Scoring**:
```python
# High consistency + high performance = higher confidence
- KDA > 4.0 with low variance
- CS/min > 7.5 with low variance
- High damage share (>30% of team)
```

**Usage**:
```python
detector = PerformanceDetector()
confidence = detector.calculate_confidence(matches, participants=participants)
```

---

## 🎨 Algorithm Pattern

### Required Method Signature

```python
def calculate_confidence(
    self,
    matches: List[Match],
    **kwargs
) -> float:
    """
    Calculate smurf confidence score.

    Args:
        matches: Player's match history (required)
        **kwargs: Additional data (player, participants, rank, etc.)

    Returns:
        Confidence score between 0 and 100
    """
```

### Best Practices

1. **Return 0-100 score** (float)
2. **Log key metrics** using structlog
3. **Handle edge cases** (empty matches, missing data)
4. **Document thresholds** in docstrings
5. **Use helper methods** for readability
6. **Accept `**kwargs`** for extensibility

### Example Template

```python
from typing import List
from ..models.matches import Match
import structlog

logger = structlog.get_logger(__name__)

class MyDetector:
    """Detect smurfs based on [describe method]."""

    def calculate_confidence(
        self,
        matches: List[Match],
        **kwargs
    ) -> float:
        """
        Calculate confidence score.

        Detection logic:
        - [Describe what triggers high confidence]
        - [Describe what triggers medium confidence]

        Returns:
            Score 0-100 (higher = more likely smurf)
        """
        # Validate input
        if not matches:
            logger.warning("no_matches_provided")
            return 0.0

        # Extract metrics
        metric_1 = self._calculate_metric_1(matches)
        metric_2 = self._calculate_metric_2(matches)

        # Scoring logic
        confidence = 0.0

        if metric_1 > THRESHOLD_1:
            confidence += 40

        if metric_2 > THRESHOLD_2:
            confidence += 30

        # Combine metrics
        if metric_1 > THRESHOLD_1 and metric_2 > THRESHOLD_2:
            confidence += 30  # Bonus for multiple signals

        logger.info(
            "detection_complete",
            metric_1=metric_1,
            metric_2=metric_2,
            confidence=confidence
        )

        return min(confidence, 100.0)

    def _calculate_metric_1(self, matches: List[Match]) -> float:
        """Helper method for calculations."""
        # Implementation
        pass
```

---

## 🧮 Combining Algorithm Scores

### Weighted Average (Current Approach)

```python
# In SmurfDetectionService
overall_confidence = (
    win_rate_score * 0.35 +
    rank_progression_score * 0.35 +
    performance_score * 0.30
)
```

### Alternative: Threshold-Based

```python
# High confidence if ANY algorithm is very confident
if any(score >= 90 for score in [win_rate, rank, performance]):
    overall = 90
# Medium if most are moderate
elif sum(score >= 60 for score in [win_rate, rank, performance]) >= 2:
    overall = 70
else:
    overall = (win_rate + rank + performance) / 3
```

### Alternative: Signal Count

```python
# Count strong signals
signals = 0
if win_rate_score >= 70: signals += 1
if rank_progression_score >= 70: signals += 1
if performance_score >= 70: signals += 1

# Map to confidence
confidence_map = {0: 20, 1: 50, 2: 75, 3: 95}
overall = confidence_map.get(signals, 20)
```

---

## 🧪 Testing Algorithms

### Unit Test Example

```python
# tests/services/test_champion_pool.py
import pytest
from app.algorithms.champion_pool import ChampionPoolDetector
from app.models.matches import Match
from app.models.participants import Participant

def test_champion_pool_limited_pool():
    """Test detection with limited champion pool."""
    detector = ChampionPoolDetector()

    # Create 30 matches with only 2 champions
    matches = [
        Match(match_id=f"MATCH_{i}", game_duration=1800)
        for i in range(30)
    ]

    participants = [
        Participant(match_id=f"MATCH_{i}", champion_id=1 if i < 20 else 2, win=True)
        for i in range(30)
    ]

    confidence = detector.calculate_confidence(matches, participants=participants)

    assert confidence >= 60  # Should be medium-high confidence
    assert confidence <= 100

def test_champion_pool_diverse():
    """Test detection with diverse champion pool."""
    detector = ChampionPoolDetector()

    matches = [Match(match_id=f"MATCH_{i}", game_duration=1800) for i in range(30)]
    participants = [
        Participant(match_id=f"MATCH_{i}", champion_id=i, win=True)  # Different champ each game
        for i in range(30)
    ]

    confidence = detector.calculate_confidence(matches, participants=participants)

    assert confidence < 30  # Should be low confidence
```

---

## 🚨 Common Pitfalls

1. **Don't return scores > 100**
   - ✅ Use `min(confidence, 100.0)`
   - ❌ Allowing scores > 100 breaks assumptions

2. **Don't ignore edge cases**
   - ✅ Handle empty matches, missing data
   - ❌ Assuming data is always complete

3. **Don't forget to log metrics**
   - ✅ Log key values for debugging
   - ❌ Silent calculations are hard to tune

4. **Don't use magic numbers**
   - ✅ Define thresholds as constants
   - ❌ Hardcoding values without explanation

5. **Don't make algorithms too complex**
   - ✅ Simple, explainable logic
   - ❌ Black-box ML without interpretability

---

## 📈 Tuning Thresholds

### Collect Real Data

```sql
-- Get distribution of win rates
SELECT
    CASE
        WHEN win_rate >= 0.7 THEN '70%+'
        WHEN win_rate >= 0.6 THEN '60-70%'
        ELSE '<60%'
    END as bucket,
    COUNT(*) as count
FROM (
    SELECT puuid, AVG(win::int) as win_rate
    FROM participants
    GROUP BY puuid
    HAVING COUNT(*) >= 30
) subquery
GROUP BY bucket;
```

### A/B Test Thresholds

```python
# Create variant algorithms
class WinRateDetectorV2(WinRateDetector):
    """Variant with adjusted thresholds."""
    HIGH_CONFIDENCE_THRESHOLD = 0.72  # Was 0.70
    MEDIUM_CONFIDENCE_THRESHOLD = 0.67  # Was 0.65
```

### Monitor False Positives

```python
# Add to detection result
result.algorithm_details = {
    "win_rate": {"score": 75, "win_rate": 0.72, "games": 45},
    "rank": {"score": 65, "level": 40, "rank": "Diamond 2"},
    "performance": {"score": 80, "avg_kda": 5.2, "avg_cs": 8.5}
}
```

---

## 🔗 Related Files

- **`../services/detection.py`** - Orchestrates algorithm execution
- **`../models/smurf_detection.py`** - Database model for results
- **`../api/detection.py`** - API endpoints for detection
- **`../tests/services/test_algorithm_integration.py`** - Integration tests

---

## 🔍 Keywords

Smurf detection, algorithms, confidence score, win rate, rank progression, performance analysis, KDA, CS per minute, champion pool, account analysis, machine learning, heuristics, thresholds, scoring
