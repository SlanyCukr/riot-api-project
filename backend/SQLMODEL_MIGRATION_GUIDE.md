# SQLModel Migration Guide

## Executive Summary

This guide documents SQLModel usage patterns, common issues, and best practices for the transition from pure SQLAlchemy to SQLModel in this project. As of the current state, we have a **mixed ORM architecture** with some features using SQLModel (auth, players) and others using pure SQLAlchemy (matches, player_analysis, settings), which is causing relationship integration issues.

## Current State Analysis

### What's Migrated to SQLModel ✅

- `app/features/auth/models.py` - Full SQLModel implementation
- `app/features/players/models.py` - Full SQLModel implementation

### What's Still Pure SQLAlchemy ⚠️

- `app/core/models.py` - Base classes using SQLAlchemy's `DeclarativeBase`
- `app/features/matches/models.py` - Using `Base`, `Mapped`, `mapped_column`
- `app/features/player_analysis/models.py` - Using `Base`, `Mapped`, `mapped_column`
- `app/features/settings/models.py` - Using `Base`, `Mapped`, `mapped_column`

### Known Issues 🐛

#### 1. Cross-ORM Relationship Problems

**In `players/models.py` (SQLModel):**
```python
# TODO: Fix MatchParticipant relationship - needs proper SQLModel to SQLAlchemy integration
# match_participations: list["MatchParticipant"] = Relationship(
#     back_populates="player",
#     sa_relationship_kwargs={"cascade": "all, delete-orphan"}
# )

# TODO: Fix SmurfDetection relationship - needs proper SQLModel to SQLAlchemy integration
# smurf_detections: list["SmurfDetection"] = Relationship(
#     back_populates="player",
#     sa_relationship_kwargs={"cascade": "all, delete-orphan"}
# )
```

**In `player_analysis/models.py` (SQLAlchemy):**
```python
# TODO: Fix Player relationship - Player is now a SQLModel class
# player = relationship("Player", back_populates="player_analysis")
```

**Root Cause:** SQLModel and SQLAlchemy models can't easily establish bidirectional relationships when they use different base classes and metaclasses.

---

## SQLModel Fundamentals

### What is SQLModel?

SQLModel combines **SQLAlchemy** (database ORM) with **Pydantic** (data validation) into a single model class. It's designed specifically for FastAPI applications.

**Key Benefits:**
- Single model definition for both database tables and API schemas
- Automatic request/response validation via Pydantic
- Type safety and IDE autocomplete
- Reduced code duplication

### The Three-Model Pattern

SQLModel follows a **Base → Table → API schemas** pattern:

```python
# 1. BASE MODEL - Shared fields between database and API
class HeroBase(SQLModel):
    name: str = Field(index=True)
    secret_name: str
    age: int | None = Field(default=None, index=True)

# 2. TABLE MODEL - Database representation (table=True)
class Hero(HeroBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    # Relationships (database-only)
    team: Team | None = Relationship(back_populates="heroes")

# 3. API MODELS - Request/response schemas
class HeroCreate(HeroBase):
    """For POST /heroes - requires only base fields"""
    pass

class HeroUpdate(SQLModel):
    """For PATCH /heroes/{id} - all fields optional"""
    name: str | None = None
    secret_name: str | None = None
    age: int | None = None

class HeroPublic(HeroBase):
    """For API responses - includes read-only fields"""
    id: int

    model_config = ConfigDict(from_attributes=True)
```

**Why This Pattern?**

1. **Base** - DRY principle: define shared fields once
2. **Table** - Database concerns (PKs, FKs, relationships, indexes)
3. **API Models** - API concerns (validation rules, optional fields for updates, response filtering)

---

## Common SQLModel Issues and Solutions

### 1. Timestamp Fields with Server Defaults

**❌ Common Mistake:**
```python
# This causes Pydantic validation errors
created_at: datetime = Field(
    sa_column_kwargs={"server_default": "NOW()"}
)
```

**✅ Correct Pattern:**
```python
from datetime import datetime
from sqlmodel import Field, SQLModel

class Player(SQLModel, table=True):
    # MUST set default=None to avoid Pydantic validation errors
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": "NOW()"},
        description="When this record was created",
    )

    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": "NOW()"},
        description="When this record was last updated",
    )
```

**Why:** When you set `server_default`, the database generates the value, not Python. Setting `default=None` tells Pydantic "this field is optional during creation, the database will fill it in."

**Alternative Pattern (if using func.now()):**
```python
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

class Player(SQLModel, table=True):
    created_at: datetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now()
        )
    )
```

### 2. Relationships Between SQLModel and SQLAlchemy Models

**Problem:** You can't use `Relationship()` from SQLModel on a SQLAlchemy model, and vice versa.

**❌ This Won't Work:**
```python
# players/models.py (SQLModel)
class Player(PlayerBase, table=True):
    analyses: list["PlayerAnalysis"] = Relationship(back_populates="player")

# player_analysis/models.py (SQLAlchemy)
class PlayerAnalysis(Base):
    player = relationship("Player", back_populates="analyses")  # ERROR!
```

**✅ Solution 1: Use `sa_relationship_kwargs` (Unidirectional)**
```python
# players/models.py (SQLModel)
class Player(PlayerBase, table=True):
    # Use SQLAlchemy's relationship via sa_relationship_kwargs
    analyses: list["PlayerAnalysis"] = Relationship(
        sa_relationship_kwargs={
            "lazy": "select",
            "cascade": "all, delete-orphan"
        }
    )

# player_analysis/models.py (SQLAlchemy)
class PlayerAnalysis(Base):
    # No relationship defined here - access is unidirectional only
    puuid: Mapped[str] = mapped_column(
        String(78),
        ForeignKey("core.players.puuid", ondelete="CASCADE")
    )
```

**✅ Solution 2: Migrate Both to SQLModel (Recommended)**
```python
# Both models use SQLModel
class Player(PlayerBase, table=True):
    analyses: list["PlayerAnalysis"] = Relationship(back_populates="player")

class PlayerAnalysis(PlayerAnalysisBase, table=True):
    player: Player = Relationship(back_populates="analyses")
```

**✅ Solution 3: Keep Both SQLAlchemy (If SQLModel doesn't fit)**
```python
# Both models use SQLAlchemy
class Player(Base):
    analyses = relationship("PlayerAnalysis", back_populates="player")

class PlayerAnalysis(Base):
    player = relationship("Player", back_populates="analyses")
```

### 3. Foreign Keys with Schema-Qualified Tables

**✅ Correct Pattern:**
```python
class PlayerRank(PlayerRankBase, table=True):
    __tablename__ = "player_ranks"
    __table_args__ = {"schema": "core"}

    # Foreign key must include schema name
    puuid: str = Field(
        foreign_key="core.players.puuid",  # schema.table.column
        max_length=78,
        index=True,
        description="Reference to the player (Riot PUUID)",
    )

    player: Player = Relationship(back_populates="ranks")
```

### 4. Indexes in SQLModel

**Important:** SQLModel no longer creates indexes by default. You must explicitly specify `index=True`.

**✅ Correct Pattern:**
```python
class Player(PlayerBase, table=True):
    # Single-column indexes
    puuid: str = Field(primary_key=True, index=True)
    riot_id: str = Field(index=True, max_length=128)

    # Composite indexes via __table_args__
    __table_args__ = (
        Index("idx_players_summoner_platform", "summoner_name", "platform"),
        Index("idx_players_riot_tag", "riot_id", "tag_line"),
        {"schema": "core"},
    )
```

### 5. Validation Doesn't Raise Errors Like Pure Pydantic

**Issue:** SQLModel doesn't always raise `ValidationError` for missing required fields like pure Pydantic models do.

**Workaround:** Use explicit validators:
```python
from pydantic import field_validator

class HeroCreate(HeroBase):
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v
```

### 6. Using `model_validate()` for ORM to Pydantic Conversion

**✅ Best Practice:**
```python
@app.post("/heroes/", response_model=HeroPublic)
def create_hero(*, session: Session = Depends(get_session), hero: HeroCreate):
    # Convert Pydantic model to table model
    db_hero = Hero.model_validate(hero)

    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)

    # FastAPI automatically converts to HeroPublic response
    return db_hero
```

### 7. Updating Models with `sqlmodel_update()`

**✅ New Method (SQLModel 0.0.14+):**
```python
@app.patch("/heroes/{hero_id}", response_model=HeroPublic)
def update_hero(
    *,
    session: Session = Depends(get_session),
    hero_id: int,
    hero: HeroUpdate
):
    db_hero = session.get(Hero, hero_id)
    if not db_hero:
        raise HTTPException(status_code=404, detail="Hero not found")

    # Update only provided fields
    hero_data = hero.model_dump(exclude_unset=True)
    db_hero.sqlmodel_update(hero_data)

    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero
```

---

## FastAPI Integration Best Practices

### 1. Response Models Filter Data

**Use `response_model` to control what's returned:**
```python
@router.get("/players/{puuid}", response_model=PlayerPublic)
async def get_player(puuid: str, db: AsyncSession = Depends(get_db)):
    player = await db.get(Player, puuid)
    # Even if Player has password_hash, PlayerPublic filters it out
    return player
```

### 2. Avoid Infinite Recursion in Nested Models

**❌ Don't Do This:**
```python
class TeamPublic(TeamBase):
    heroes: list["HeroPublic"] = []

class HeroPublic(HeroBase):
    team: TeamPublic | None = None  # Infinite recursion!
```

**✅ Do This:**
```python
# Use simple models for nested relationships
class TeamPublic(TeamBase):
    id: int

class HeroPublic(HeroBase):
    id: int
    team: TeamPublic | None = None  # TeamPublic doesn't include heroes

# Separate model for detailed team view
class TeamPublicWithHeroes(TeamPublic):
    heroes: list[HeroPublic] = []  # HeroPublic doesn't include team details
```

### 3. Separate Create/Update/Read Models

**✅ Best Practice:**
```python
# Create - requires only necessary fields
class PlayerCreate(PlayerBase):
    pass

# Update - all fields optional
class PlayerUpdate(SQLModel):
    summoner_name: str | None = None
    account_level: int | None = None
    is_tracked: bool | None = None

# Public - includes read-only fields
class PlayerPublic(PlayerBase):
    puuid: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### 4. Exclude Sensitive Fields

**Use `exclude=True` for sensitive data:**
```python
class User(UserBase, table=True):
    password_hash: str = Field(
        description="Hashed password using Argon2id",
        exclude=True,  # Never included in API responses
    )
```

---

## Migration Strategy

### Phase 1: Analyze Dependencies

1. **Identify relationship clusters:**
   - Players ↔ PlayerRanks ✅ (both SQLModel)
   - Players ↔ Matches ↔ MatchParticipants ⚠️ (mixed)
   - Players ↔ PlayerAnalysis ⚠️ (mixed)

2. **Map foreign key relationships:**
   ```bash
   # Find all foreign keys pointing to players
   grep -r "ForeignKey.*players" backend/app/features/
   ```

### Phase 2: Migrate in Clusters

**Recommended Migration Order:**

1. ✅ **Auth** (already done)
2. ✅ **Players + PlayerRanks** (already done)
3. **Settings** (standalone, no complex relationships)
4. **Matches + MatchParticipants** (cluster migration)
5. **PlayerAnalysis** (depends on Players, already SQLModel)

**Example: Migrating Settings**

```python
# BEFORE (SQLAlchemy)
class SystemSetting(Base):
    __tablename__ = "system_settings"
    __table_args__ = {"schema": "jobs"}

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)

# AFTER (SQLModel)
class SystemSettingBase(SQLModel):
    value: str = Field(description="Setting value")
    category: str = Field(max_length=64, description="Setting category")

class SystemSetting(SystemSettingBase, table=True):
    __tablename__ = "system_settings"
    __table_args__ = {"schema": "jobs"}

    key: str = Field(primary_key=True, max_length=128, description="Setting key")

    # Timestamps with server defaults
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": "NOW()"}
    )

class SystemSettingPublic(SystemSettingBase):
    key: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### Phase 3: Handle Relationship Edges

**For mixed relationships during transition:**

```python
# Option A: Temporarily make relationship unidirectional
class Player(PlayerBase, table=True):
    # Remove back_populates during transition
    analyses: list["PlayerAnalysis"] = Relationship()

# Option B: Use string-based relationship (SQLAlchemy feature)
class PlayerAnalysis(PlayerAnalysisBase, table=True):
    player: "Player" = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[PlayerAnalysis.puuid]",
            "primaryjoin": "Player.puuid == PlayerAnalysis.puuid"
        }
    )
```

### Phase 4: Update Alembic Migrations

**After migrating a model, create a migration:**
```bash
docker compose exec backend uv run alembic revision --autogenerate -m "migrate matches to SQLModel"
docker compose exec backend uv run alembic upgrade head
```

**Important:** SQLModel models generate the same SQL schema as SQLAlchemy models, so migrations should show "no changes" if done correctly.

---

## Testing After Migration

### Unit Tests

```python
import pytest
from sqlmodel import Session, create_engine, SQLModel

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_create_hero(session: Session):
    hero = Hero(name="Spider-Boy", secret_name="Pedro")
    session.add(hero)
    session.commit()
    session.refresh(hero)

    assert hero.id is not None
    assert hero.name == "Spider-Boy"
```

### Integration Tests

```python
from httpx import AsyncClient
from fastapi.testclient import TestClient

async def test_create_hero_endpoint(client: AsyncClient):
    response = await client.post(
        "/api/v1/heroes/",
        json={"name": "Spider-Boy", "secret_name": "Pedro", "age": 16}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Spider-Boy"
    assert "id" in data
```

---

## Troubleshooting

### Issue: "No module named 'sqlmodel'"

**Solution:**
```bash
docker compose exec backend uv pip install sqlmodel
# or rebuild
docker compose build backend
```

### Issue: Alembic detects changes after SQLModel migration

**Possible Causes:**
1. Changed column types (e.g., `String(64)` → `String(128)`)
2. Changed nullable constraints
3. Changed default values

**Solution:** Review the migration carefully and ensure schema matches exactly.

### Issue: Relationship lazy loading fails

**Solution:** Use explicit `sa_relationship_kwargs`:
```python
team: Team | None = Relationship(
    back_populates="heroes",
    sa_relationship_kwargs={"lazy": "joined"}  # or "select", "selectin"
)
```

### Issue: Pydantic validation errors on server defaults

**Solution:** Always use `default=None` for server-side defaults:
```python
created_at: datetime = Field(default=None, sa_column_kwargs={"server_default": "NOW()"})
```

---

## References

- **Official SQLModel Docs:** https://sqlmodel.tiangolo.com/
- **FastAPI Integration:** https://sqlmodel.tiangolo.com/tutorial/fastapi/
- **SQLAlchemy 2.0 Docs:** https://docs.sqlalchemy.org/en/20/
- **Pydantic V2 Docs:** https://docs.pydantic.dev/latest/

---

## Current Project Status Summary

### ✅ Successfully Migrated (7/7 - 100% COMPLETE!)
- `app/features/auth/models.py` - Full SQLModel with proper patterns
- `app/features/players/models.py` - Full SQLModel with proper patterns
- `app/features/settings/models.py` - Full SQLModel with proper patterns
- `app/features/matches/models.py` + `participants.py` - Full SQLModel with proper patterns
- `app/features/player_analysis/models.py` - Full SQLModel with proper patterns
- `app/features/jobs/models.py` - Full SQLModel with proper patterns
- `app/features/matchmaking_analysis/models.py` - Full SQLModel with proper patterns

### ⚠️ External Library Tables
- `apscheduler_jobs` - Managed by APScheduler library (not in our codebase)
  - APScheduler creates and manages its own schema
  - Excluded from Alembic autogenerate via `include_object()` filter

### ✅ Resolved Issues
1. ~~**Cross-ORM Relationships**~~ - All features now use SQLModel, no more mixed ORM ✅
2. ~~**Blocked migrations**~~ - All 7 features successfully migrated ✅
3. ~~**Alembic metadata configuration**~~ - Now uses only `SQLModel.metadata` ✅
4. ~~**Commented-out relationships**~~ - All relationships now enabled and functional ✅:
   - `Player.match_participations` ↔ `MatchParticipant.player` ✅
   - `Player.player_analyses` ↔ `PlayerAnalysis.player` ✅
5. ~~**Index naming conventions**~~ - Renamed from `ix_app_*` to `ix_core_*/ix_jobs_*/ix_auth_*` ✅ (October 27, 2025)
6. ~~**Base class cleanup**~~ - Removed unused `Base` class from `core/models.py` ✅ (October 27, 2025)
7. ~~**Documentation updates**~~ - All AGENTS.md files now reflect SQLModel patterns ✅ (October 27, 2025)

### 🎯 Architecture Achievements
1. **Pure SQLModel codebase** - All application models use SQLModel ✅
2. **Simplified Alembic** - Uses only `SQLModel.metadata` (no Base.metadata mixing) ✅
3. **Bidirectional relationships** - All SQLModel relationships functional ✅
4. **Consistent index naming** - All indexes follow SQLModel convention with schema prefixes ✅
5. **Clean core module** - `core/models.py` simplified, Base class removed ✅
6. **Updated documentation** - All AGENTS.md files reflect current SQLModel patterns ✅

### 📋 Optional Future Enhancements
1. **Create API response schemas** for SQLModel models (optional)
2. **Performance testing** to ensure no regressions from SQLModel migration
3. ~~**Address Alembic autogenerate sensitivity**~~ ✅ **RESOLVED** (October 28, 2025)
   - **Root Cause**: Missing `include_schemas=True` in env.py configuration
   - **Symptom**: Alembic only scanned `public` schema (default), but tables are in `core`, `auth`, `jobs` schemas
   - **Fix**: Added `include_schemas=True` + `include_name` filter to `backend/alembic/env.py`
   - **Result**: Autogenerate now works correctly for multi-schema PostgreSQL setup

---

**Last Updated:** October 28, 2025 - **SQLModel MIGRATION FULLY COMPLETE + Alembic Fixed** 🎉✨

All application models now use SQLModel. Database schema synchronized with proper index naming. Base class removed. Documentation updated. **Alembic autogenerate now properly handles multi-schema PostgreSQL setup.**
