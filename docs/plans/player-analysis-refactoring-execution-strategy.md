# Player Analysis Feature: Enterprise Patterns Refactoring - Subagent Execution Strategy

**Date**: 2025-10-30
**Scope**: Refactor player_analysis feature from current architecture to enterprise patterns
**Pattern Source**: Successfully proven in `refactor/players-sqlalchemy-enterprise` branch
**Estimated Complexity**: Medium-High (multi-phase refactoring)

---

## 📋 Current State Analysis

### Current Architecture

- ✅ **Modular Analyzers**: Already implemented (5 analyzers in `analyzers/` directory)
- ✅ **Service Layer**: Exists but contains direct SQL queries
- ✅ **SQLAlchemy Models**: Uses SQLAlchemy 2.0+ ORM models
- ❌ **Repository Pattern**: Not implemented (queries in service)
- ❌ **Rich Domain Models**: No business logic in models
- ❌ **Transformers**: No ORM → Pydantic mapping layer

### Files to Refactor

- `backend/app/features/player_analysis/service.py` - 687 lines (remove SQL, use repository)
- `backend/app/features/player_analysis/models.py` - Extract business logic
- `backend/app/features/player_analysis/analyzers/*.py` - Make pure (no DB dependency)
- `backend/app/features/player_analysis/router.py` - Minimal updates for DI

### Dependencies on Other Features

- `features.players` - Uses `PlayerORM` (already refactored)
- `features.matches` - Uses match data (needs refactoring too)
- `core.riot_api` - Uses `RiotDataManager`

---

## 🎯 Refactoring Goals

1. **Repository Pattern** - Isolate all SQL queries to repository layer
2. **Rich Domain Models** - Add business logic to ORM models
3. **Pure Analyzers** - Remove database dependencies from analyzers
4. **Data Mapper** - Create transformers for ORM ↔ Pydantic conversion
5. **Thin Service** - Service as pure orchestration layer
6. **Type Safety** - Full SQLAlchemy 2.0 mapped types

---

## 📊 10-Phase Execution Strategy

### Phase Dependencies Graph

```
Phase 1 → Phase 2 → Phase 4
   ↓         ↓         ↓
Phase 3 → Phase 5 → Phase 7 → Phase 9 → Phase 10
                     ↓
                   Phase 8
```

### Phase 1: Create ORM Models with Business Logic

**Priority**: Critical Path
**Dependencies**: None
**Parallelizable**: ✅ Yes

#### What to Create

**File**: `backend/app/features/player_analysis/orm_models.py`

**Implementation**:

```python
class PlayerAnalysisORM(Base):
    """Rich domain model with business logic."""

    def is_high_confidence_detection(self) -> bool:
        """Check if detection has high confidence."""
        return self.confidence in ["high", "very_high"]

    def calculate_factor_breakdown(self) -> Dict[str, float]:
        """Get normalized factor scores."""
        return {
            "win_rate": float(self.win_rate_score or 0),
            "kda": float(self.kda_score or 0),
            # ... all factors
        }

    def needs_reanalysis(self, hours: int = 24) -> bool:
        """Check if analysis is stale."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return self.last_analysis < cutoff

    def get_detected_factors(self) -> List[str]:
        """Get list of factors that triggered detection."""
        factors = []
        if self.win_rate_score and self.win_rate_score > 0.5:
            factors.append("win_rate")
        # ... check other factors
        return factors
```

#### Subagent Tasks

1. **Subagent 1A**: Extract PlayerAnalysis model with business logic
2. **Subagent 1B**: Add helper methods for score calculations
3. **Subagent 1C**: Add validation methods

**Estimated Time**: 2-3 hours
**Testing**: Unit tests for business logic methods

---

### Phase 2: Create Repository Layer

**Priority**: Critical Path
**Dependencies**: Phase 1
**Parallelizable**: ❌ No (depends on Phase 1)

#### What to Create

**File**: `backend/app/features/player_analysis/repository.py`

**Implementation**:

```python
class PlayerAnalysisRepositoryInterface(ABC):
    """Repository interface for player analysis."""

    @abstractmethod
    async def get_by_puuid(self, puuid: str) -> Optional[PlayerAnalysisORM]:
        pass

    @abstractmethod
    async def create_analysis(
        self,
        puuid: str,
        analysis_data: Dict[str, Any]
    ) -> PlayerAnalysisORM:
        pass

    @abstractmethod
    async def get_recent_analysis(
        self,
        puuid: str,
        hours: int = 24
    ) -> Optional[PlayerAnalysisORM]:
        pass

    @abstractmethod
    async def get_stale_analyses(
        self,
        hours: int = 168  # 1 week
    ) -> List[PlayerAnalysisORM]:
        pass

class SQLAlchemyPlayerAnalysisRepository:
    """SQLAlchemy implementation."""

    async def get_by_puuid(self, puuid: str) -> Optional[PlayerAnalysisORM]:
        stmt = select(PlayerAnalysisORM).where(
            PlayerAnalysisORM.puuid == puuid
        ).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
```

#### Subagent Tasks

1. **Subagent 2A**: Create repository interface (12 methods)
2. **Subagent 2B**: Implement SQLAlchemy repository with all queries
3. **Subagent 2C**: Add composite query methods (recent analyses, stats)

**Estimated Time**: 3-4 hours
**Testing**: Integration tests for all repository methods

---

### Phase 3: Create Data Transformers

**Priority**: Foundation
**Dependencies**: Phase 1
**Parallelizable**: ✅ Yes (can run after Phase 1)

#### What to Create

**File**: `backend/app/features/player_analysis/transformers.py`

**Implementation**:

```python
def player_analysis_orm_to_response(
    orm: PlayerAnalysisORM,
) -> DetectionResponse:
    """Transform PlayerAnalysisORM to DetectionResponse."""
    return DetectionResponse(
        puuid=orm.puuid,
        is_smurf=orm.is_smurf,
        detection_score=float(orm.smurf_score),
        confidence_level=orm.confidence or "none",
        factors=_extract_factors(orm),  # Build from stored scores
        reason=_generate_reason(orm),
        sample_size=orm.games_analyzed,
        created_at=orm.created_at,
        analysis_time_seconds=0.0,
    )

def detection_response_to_orm(
    response: DetectionResponse,
    player: PlayerORM,
) -> PlayerAnalysisORM:
    """Transform DetectionResponse to PlayerAnalysisORM."""
    return PlayerAnalysisORM(
        puuid=response.puuid,
        is_smurf=response.is_smurf,
        confidence=response.confidence_level,
        smurf_score=Decimal(str(response.detection_score)),
        # ... map all fields
    )
```

#### Subagent Tasks

1. **Subagent 3A**: Create ORM → Response transformers (3-4 functions)
2. **Subagent 3B**: Create Response → ORM transformers
3. **Subagent 3C**: Add transformer validation and error handling

**Estimated Time**: 2 hours
**Testing**: Unit tests for all transformers

---

### Phase 4: Refactor Service Layer (Core Methods)

**Priority**: Critical Path
**Dependencies**: Phases 2, 3
**Parallelizable**: ❌ No (sequential refactoring)

#### What to Refactor

**File**: `backend/app/features/player_analysis/service.py`

**Methods to Refactor** (Core 5):

1. `analyze_player()` - Main analysis orchestrator
2. `_get_player()` - Use repository
3. `_store_detection_result()` - Use repository
4. `_get_recent_detection()` - Use repository
5. `_mark_matches_processed()` - Use repository

**Pattern**:

```python
# BEFORE (Lines 300-305):
async def _get_player(self, puuid: str) -> Optional[PlayerORM]:
    result = await self.db.execute(
        select(PlayerORM).where(PlayerORM.puuid == puuid).limit(1)
    )
    return result.scalar_one_or_none()

# AFTER:
async def _get_player(self, puuid: str) -> Optional[PlayerORM]:
    return await self.player_repository.get_by_puuid(puuid)
```

#### Subagent Tasks

1. **Subagent 4A**: Refactor analyze_player() to use repository (686 → ~400 lines)
2. **Subagent 4B**: Refactor \_get_player() and \_get_recent_detection()
3. **Subagent 4C**: Refactor \_store_detection_result() and \_mark_matches_processed()

**Estimated Time**: 3-4 hours
**Testing**: Integration test the analyze_player flow

---

### Phase 5: Refactor Match Data Access

**Priority**: High
**Dependencies**: Phases 2, 4
**Parallelizable**: ✅ Yes (can run after Phases 2, 4)

#### What to Refactor

**File**: `backend/app/features/player_analysis/service.py`

**Method**: `_get_recent_matches()` (Lines 307-373)

**Pattern**:

```python
# Create in repository.py:
async def get_recent_matches_for_analysis(
    self,
    puuid: str,
    min_games: int,
    queue_filter: Optional[int] = None,
    time_period_days: Optional[int] = None,
    limit: int = 50,
) -> tuple[List[Dict[str, Any]], List[str]]:
    """Get recent matches with participant data."""
    # Complex SQL query moved here
    pass

# In service.py:
async def _get_recent_matches(self, ...):
    return await self.analysis_repository.get_recent_matches_for_analysis(...)
```

#### Subagent Tasks

1. **Subagent 5A**: Extract \_get_recent_matches() to repository
2. **Subagent 5B**: Add match filtering logic to repository
3. **Subagent 5C**: Add performance optimizations (indexes, limits)

**Estimated Time**: 2-3 hours
**Testing**: Test match retrieval with various filters

---

### Phase 6: Refactor Remaining Service Methods

**Priority**: Medium
**Dependencies**: Phases 2, 4, 5
**Parallelizable**: ✅ Yes

#### Methods to Refactor

1. `_get_current_rank()` - Query rank data via repository
2. Service initialization - Inject repositories

#### Subagent Tasks

1. **Subagent 6A**: Refactor \_get_current_rank()
2. **Subagent 6B**: Update service initialization for DI
3. **Subagent 6C**: Remove all `self.db.execute()` calls

**Estimated Time**: 1-2 hours
**Testing**: Verify all service methods work

---

### Phase 7: Refactor Analyzers (Make Pure)

**Priority**: High
**Dependencies**: Phase 4 (analyzers called from service)
**Parallelizable**: ✅ Yes (each analyzer independent)

**Files**: All analyzers in `backend/app/features/player_analysis/analyzers/`

**Refactoring Goal**: Remove database session dependency

**Current Pattern**:

```python
async def analyze(self, puuid, recent_matches, player, db):
    # Has db parameter but doesn't use it
    pass
```

**New Pattern**:

```python
async def analyze(self, puuid, recent_matches, player):
    # No db parameter - pure function
    pass
```

#### Subagent Tasks

1. **Subagent 7A**: Refactor win_rate_analyzer.py (remove db)
2. **Subagent 7B**: Refactor win_rate_trend_analyzer.py
3. **Subagent 7C**: Refactor account_level_analyzer.py
4. **Subagent 7D**: Refactor performance_analyzer.py
5. **Subagent 7E**: Refactor rank_progression_analyzer.py
6. **Subagent 7F**: Update base_analyzer.py interface
7. **Subagent 7G**: Update service.py to call analyzers without db

**Estimated Time**: 3-4 hours
**Testing**: Unit tests for each analyzer

---

### Phase 8: Update Dependencies & DI

**Priority**: Medium
**Dependencies**: Phases 2, 4, 7
**Parallelizable**: ✅ Yes

#### What to Update

**File**: `backend/app/features/player_analysis/dependencies.py`

**Implementation**:

```python
from app.features.player_analysis.repository import PlayerAnalysisRepositoryInterface
from app.features.player_analysis.service import PlayerAnalysisService
from app.features.players.repository import PlayerRepositoryInterface

def get_player_analysis_repository(
    db: AsyncSession = Depends(get_db)
) -> PlayerAnalysisRepositoryInterface:
    return SQLAlchemyPlayerAnalysisRepository(db)

def get_player_analysis_service(
    analysis_repo: PlayerAnalysisRepositoryInterface = Depends(get_player_analysis_repository),
    player_repo: PlayerRepositoryInterface = Depends(get_player_repository),
    data_manager: RiotDataManager = Depends(get_riot_data_manager),
    db: AsyncSession = Depends(get_db),
) -> PlayerAnalysisService:
    return PlayerAnalysisService(
        analysis_repository=analysis_repo,
        player_repository=player_repo,
        data_manager=data_manager,
        db=db,
    )
```

#### Subagent Tasks

1. **Subagent 8A**: Update dependencies.py with repository injection
2. **Subagent 8B**: Update service.py constructor for DI
3. **Subagent 8C**: Update router.py if needed

**Estimated Time**: 1-2 hours
**Testing**: Integration test DI container

---

### Phase 9: Integration Testing

**Priority**: Critical
**Dependencies**: All Phases 1-8
**Parallelizable**: ❌ No

#### Test Scenarios

1. **End-to-End Analysis Flow**

   - Analyze a player from start to finish
   - Verify all factors calculated correctly
   - Check database storage

2. **Repository Methods**

   - Test all CRUD operations
   - Test complex queries (recent analyses, stale analyses)

3. **Analyzers**

   - Unit test each analyzer independently
   - Test edge cases (empty data, errors)

4. **Service Orchestration**
   - Test analyze_player() with various inputs
   - Test error handling
   - Test caching (recent analysis)

#### Subagent Tasks

1. **Subagent 9A**: Write repository integration tests
2. **Subagent 9B**: Write analyzer unit tests
3. **Subagent 9C**: Write service integration tests
4. **Subagent 9D**: End-to-end API testing

**Estimated Time**: 4-5 hours
**Testing**: Full test suite execution

---

### Phase 10: Performance Optimization & Documentation

**Priority**: Low
**Dependencies**: Phase 9 (must verify correctness first)
**Parallelizable**: ✅ Yes

#### Tasks

1. **Performance Optimization**

   - Add database indexes for query optimization
   - Add query result caching
   - Optimize match retrieval queries

2. **Documentation**

   - Update README.md with enterprise architecture
   - Document new patterns used
   - Create migration summary

3. **Code Quality**
   - Run all linters and type checkers
   - Verify cyclomatic complexity < 10
   - Ensure 90%+ test coverage

#### Subagent Tasks

1. **Subagent 10A**: Optimize database queries and add indexes
2. **Subagent 10B**: Add query caching layer
3. **Subagent 10C**: Update documentation and README
4. **Subagent 10D**: Final code quality checks

**Estimated Time**: 3-4 hours
**Testing**: Performance benchmarks

---

## 🚀 Parallel Execution Groups

### Group 1: Foundation (Can run in parallel)

**Phases**: 1, 3
**Time**: 4-5 hours total
**Reason**: No dependencies between phases, both create foundational components

- **Phase 1**: ORM Models with Business Logic
- **Phase 3**: Data Transformers

### Group 2: Repository Layer (Sequential)

**Phases**: 2
**Time**: 3-4 hours
**Reason**: Depends on Phase 1

- **Phase 2**: Create Repository Layer

### Group 3: Service Refactoring (Sequential)

**Phases**: 4, 5, 6
**Time**: 6-9 hours total
**Reason**: Each phase depends on previous

- **Phase 4**: Refactor Service Layer (Core Methods)
- **Phase 5**: Refactor Match Data Access
- **Phase 6**: Refactor Remaining Service Methods

### Group 4: Analyzers (Parallel)

**Phases**: 7
**Time**: 3-4 hours total (parallel)
**Reason**: Each analyzer is independent

- **Phase 7**: Refactor Analyzers (5 analyzers can run in parallel)

### Group 5: Integration (Sequential)

**Phases**: 8, 9, 10
**Time**: 8-11 hours total
**Reason**: Each depends on previous

- **Phase 8**: Update Dependencies & DI
- **Phase 9**: Integration Testing
- **Phase 10**: Performance Optimization & Documentation

---

## 📅 Optimal Execution Order

### Option A: Maximum Parallelism (Recommended)

**Total Time**: ~21-28 hours over 2-3 days

```
Day 1 (8 hours):
  ├─ Phase 1: ORM Models (3 hours)
  ├─ Phase 2: Repository Layer (4 hours) [depends on 1]
  └─ Phase 3: Transformers (2 hours) [parallel with 1]

Day 2 (8 hours):
  ├─ Phase 4: Service Refactor - Core (4 hours) [depends on 2, 3]
  └─ Phase 5-6: Service Refactor - Match Data & Remaining (4 hours) [depends on 4]

Day 3 (8 hours):
  ├─ Phase 7: Analyzers Refactor (4 hours) [parallelizable]
  ├─ Phase 8: Dependencies & DI (2 hours) [depends on 2, 4, 7]
  └─ Phase 9: Integration Testing (2 hours) [depends on 8]

Day 4 (4 hours):
  └─ Phase 10: Optimization & Documentation (4 hours) [depends on 9]
```

### Option B: Sequential (Safe)

**Total Time**: ~25-32 hours over 3-4 days

Run each phase sequentially, especially if limited subagents available.

---

## ✅ Success Criteria

### For Each Batch

1. **Batch 1 (Phases 1-3)**

   - [ ] ORM models created with 5+ business logic methods
   - [ ] Repository interface defined with 12+ methods
   - [ ] Transformers handle all ORM ↔ Pydantic conversions

2. **Batch 2 (Phases 4-6)**

   - [ ] Service has 0 `self.db.execute()` calls
   - [ ] All SQL queries moved to repository
   - [ ] Service methods average < 30 lines

3. **Batch 3 (Phase 7)**

   - [ ] All analyzers have no `db` parameter
   - [ ] All analyzer tests pass independently
   - [ ] Base analyzer interface updated

4. **Batch 4 (Phases 8-10)**
   - [ ] Dependency injection working correctly
   - [ ] Integration tests pass (95%+ success rate)
   - [ ] End-to-end analysis works through API
   - [ ] Performance benchmarks meet targets

### Overall Success

- [ ] 100% of existing functionality preserved
- [ ] New enterprise patterns established
- [ ] Service layer 40-50% smaller
- [ ] All SQL isolated to repository layer
- [ ] Test coverage ≥ 90%
- [ ] Code quality checks pass

---

## 🔗 Dependencies Between Features

### Requires (Must be refactored first)

- ✅ **players** - Already refactored (reference pattern)
- ⚠️ **matches** - Currently uses service pattern, may need work

### Affected By This Refactoring

- **jobs** - Background job for player analysis
- **matchmaking_analysis** - Depends on player analysis results

### Mitigation

- Keep backward-compatible API during refactoring
- Test jobs feature after Phase 9
- Document any API changes

---

## 📚 Reference Patterns

### From players feature migration:

- `backend/app/features/players/orm_models.py` - Rich domain models
- `backend/app/features/players/repository.py` - Repository pattern
- `backend/app/features/players/service.py` - Thin service layer
- `backend/app/features/players/transformers.py` - Data mapping
- `backend/app/features/players/MIGRATION_SUMMARY.md` - Migration guide

### Pattern Templates:

- `docs/plans/enterprise-patterns-guide.md` - Reusable patterns
- `docs/plans/players-feature-enterprise-patterns.md` - Detailed guide

---

## ⚠️ Risk Mitigation

### Risk 1: Breaking Existing API

**Mitigation**: Keep public API signatures identical, only refactor internal implementation

### Risk 2: Data Loss During Migration

**Mitigation**: No schema changes in Phase 1-10, only refactoring existing structure

### Risk 3: Performance Degradation

**Mitigation**:

- Add indexes in Phase 10
- Use same queries, just move to repository
- Benchmark before/after

### Risk 4: Test Coverage Gaps

**Mitigation**:

- Write tests before refactoring (Phase 9)
- Run full test suite after each batch
- Manual testing through UI

---

## 📞 Questions?

This execution strategy is designed to:

1. **Minimize risk** - Each batch is atomic and testable
2. **Maximize parallelism** - Independent phases run in parallel
3. **Follow proven pattern** - Uses same approach as successful players feature
4. **Ensure quality** - Testing and validation at each stage

The pattern is proven and ready to scale from the players feature success!
