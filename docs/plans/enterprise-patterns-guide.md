# Enterprise Architecture Patterns Guide

**Purpose**: Reusable template for implementing enterprise-grade architecture patterns in any feature
**Date**: 2025-10-28
**Based On**: Martin Fowler's *Patterns of Enterprise Application Architecture*, FastAPI best practices, SQLAlchemy 2.0, Pydantic v2

---

## Table of Contents

1. [Pattern Catalog](#pattern-catalog)
2. [Decision Matrices](#decision-matrices)
3. [Code Templates](#code-templates)
4. [Type Safety Configuration](#type-safety-configuration)
5. [Testing Templates](#testing-templates)
6. [Best Practices](#best-practices)
7. [Common Pitfalls](#common-pitfalls)
8. [Feature Migration Checklist](#feature-migration-checklist)

---

## Pattern Catalog

### 1. Repository Pattern

**Source**: Martin Fowler, *Patterns of Enterprise Application Architecture*

**Definition**:
> "Mediates between the domain and data mapping layers using a collection-like interface for accessing domain objects."

**Problem It Solves**:
- Complexity in systems with intricate domain models
- Duplicate query logic scattered across codebase
- Tight coupling between business logic and database
- Difficulty testing business logic in isolation

**How It Works**:
```
Business Logic
      ↓
Repository Interface (collection-like: get, find, add, remove)
      ↓
Repository Implementation (SQL queries, ORM operations)
      ↓
Database
```

**Key Characteristics**:
- Acts as **in-memory collection** from client perspective
- **Encapsulates** all database access logic
- Provides **collection semantics**: get, find, add, remove, save
- Returns **domain objects** (ORM models), not raw data
- **One-way dependency**: domain depends on repository interface, never on implementation

**When to Use**:
- ✅ Multiple endpoints reuse same queries
- ✅ Need to swap database implementations (testing, migration)
- ✅ Want to mock data access in tests
- ✅ Complex domain with many database operations
- ✅ Team size > 3 developers (clear responsibility boundaries)

**When NOT to Use**:
- ❌ Simple CRUD with single table (over-engineering)
- ❌ Microservice with < 5 database operations
- ❌ Prototyping/MVPs (premature abstraction)

**Code Pattern**:
```python
# Interface
class EntityRepositoryInterface(ABC):
    @abstractmethod
    async def get_by_id(self, id: int) -> EntityORM | None:
        """Get entity by ID - collection semantics."""
        pass

    @abstractmethod
    async def find_by_criteria(self, **filters) -> list[EntityORM]:
        """Find entities matching criteria - query semantics."""
        pass

    @abstractmethod
    async def add(self, entity: EntityORM) -> EntityORM:
        """Add entity to collection."""
        pass

    @abstractmethod
    async def remove(self, entity: EntityORM) -> None:
        """Remove entity from collection."""
        pass

# Implementation
class SQLAlchemyEntityRepository(EntityRepositoryInterface):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, id: int) -> EntityORM | None:
        stmt = select(EntityORM).where(EntityORM.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
```

**Benefits**:
- ✅ **Testability**: Mock repository interface in service tests
- ✅ **Flexibility**: Swap database implementation (PostgreSQL → MongoDB)
- ✅ **Maintainability**: All queries in one place
- ✅ **Reusability**: Multiple services use same repository
- ✅ **Type Safety**: Interface defines contract

**Trade-offs**:
- ⚠️ Extra boilerplate (interface + implementation)
- ⚠️ Learning curve for junior developers
- ⚠️ Can become bloated if not careful (too many methods)

---

### 2. Rich Domain Model Pattern

**Source**: Martin Fowler, *Patterns of Enterprise Application Architecture*

**Definition**:
> "An object model of the domain that incorporates both behavior and data."

**Problem It Solves**:
- **Anemic Domain Models**: Models that are just getters/setters with no behavior
- Business logic scattered in service classes (procedural design in OO clothing)
- Duplication of domain logic across multiple services
- Unclear where business rules belong

**The Anti-Pattern (Anemic Domain Model)**:
```python
# Anemic - just data, no behavior
class Player:
    puuid: str
    account_level: int
    wins: int
    losses: int
    # No methods!

# All logic in service (procedural style)
class PlayerService:
    def calculate_win_rate(self, player: Player) -> float:
        total = player.wins + player.losses
        return (player.wins / total * 100) if total > 0 else 0.0

    def is_smurf(self, player: Player) -> bool:
        if player.account_level < 30:
            if self.calculate_win_rate(player) > 65:
                return True
        return False
```

**The Correct Pattern (Rich Domain Model)**:
```python
# Rich - data + behavior together
class Player:
    puuid: str
    account_level: int
    wins: int
    losses: int

    # Business behavior on own data
    def calculate_win_rate(self) -> float:
        """Calculate win rate - domain logic."""
        total = self.wins + self.losses
        return (self.wins / total * 100) if total > 0 else 0.0

    def is_new_account(self) -> bool:
        """Business rule encapsulated."""
        return self.account_level < 30

    def is_smurf(self) -> bool:
        """Complex business logic using other methods."""
        return self.is_new_account() and self.calculate_win_rate() > 65

# Service becomes thin
class PlayerService:
    async def check_for_smurfs(self) -> list[Player]:
        players = await self.repo.get_all()
        # Domain model contains the logic
        return [p for p in players if p.is_smurf()]
```

**Key Principle** (Martin Fowler):
> "The Service Layer is thin - all the key logic lies in the domain layer."

**When to Use**:
- ✅ Complex business rules
- ✅ Domain calculations needed in multiple places
- ✅ Validation rules that depend on entity state
- ✅ Business operations that change entity state

**What Belongs in Domain Models**:
- ✅ Calculations on entity's own data (win rate, totals, averages)
- ✅ Business rules (is new account? needs refresh? is valid?)
- ✅ Validation logic (validate for tracking, can be deleted?)
- ✅ State transitions (mark as tracked, activate, deactivate)
- ✅ Derived properties (display rank, smurf score)

**What Does NOT Belong in Domain Models**:
- ❌ Database queries (belongs in repository)
- ❌ External API calls (belongs in gateway/service)
- ❌ Orchestration across multiple entities (belongs in service)
- ❌ Transaction management (belongs in service)
- ❌ DTO transformations (belongs in transformer)

**Benefits**:
- ✅ **Encapsulation**: Business rules close to data
- ✅ **Reusability**: Logic available wherever entity is used
- ✅ **Testability**: Test domain logic without database
- ✅ **Clarity**: Obvious where business rules live
- ✅ **Maintainability**: Changes to rules in one place

---

### 3. Data Mapper Pattern

**Source**: Martin Fowler, *Patterns of Enterprise Application Architecture*

**Definition**:
> "A layer of mappers that moves data between objects and a database while keeping them independent of each other and the mapper itself."

**Comparison: Data Mapper vs Active Record**

| Aspect | Data Mapper (SQLAlchemy) | Active Record (Rails, Django ORM) |
|--------|-------------------------|----------------------------------|
| **Database Knowledge** | Domain objects unaware of database | Objects have `.save()`, `.delete()` |
| **Persistence Handling** | Session object handles persistence | Objects handle own persistence |
| **Coupling** | Loose (domain independent) | Tight (domain coupled to DB) |
| **Complexity** | Higher (more separation) | Lower (simpler for CRUD) |
| **Testing** | Easy (objects work without DB) | Harder (objects tied to DB) |
| **Use Case** | Complex domains | Simple CRUD apps |

**SQLAlchemy 2.0 Follows Data Mapper**:
```python
# Domain object doesn't know about database
class PlayerORM(Base):
    puuid: Mapped[str] = mapped_column(String(78), primary_key=True)
    account_level: Mapped[int] = mapped_column(Integer)

    # Business logic, no .save() or .delete()
    def is_new_account(self) -> bool:
        return self.account_level < 30

# Session handles persistence (Data Mapper)
player = PlayerORM(puuid="123", account_level=25)
session.add(player)  # Session knows how to persist
await session.commit()
```

**Active Record Pattern** (for comparison):
```python
# In Django ORM or Rails ActiveRecord
class Player(models.Model):
    puuid = models.CharField(max_length=78)
    account_level = models.IntegerField()

    def save_to_database(self):
        self.save()  # Object handles own persistence
```

**Why Data Mapper for This Project**:
- ✅ Complex domain (players, matches, analysis, etc.)
- ✅ Need to test domain logic without database
- ✅ Domain model doesn't match database 1:1 (Riot API transformations)
- ✅ SQLAlchemy 2.0 provides excellent Data Mapper implementation

---

### 4. Anti-Corruption Layer (ACL)

**Source**: Martin Fowler, Domain-Driven Design

**Definition**:
> "Creates isolation between subsystems that don't share the same semantics."

**Problem It Solves**:
- External system has different semantics than your domain
- External system may have quality issues or poor design
- Direct integration forces your domain to adopt external patterns
- Changes in external system ripple through your codebase

**Real-World Example: Riot API Integration**

**Without ACL** (BAD):
```python
# Service directly uses Riot API DTOs
class PlayerService:
    async def create_player(self, game_name: str, tag: str):
        # Riot API returns camelCase DTOs
        riot_account = await self.riot_client.get_account(game_name, tag)

        # Riot semantics leak into service
        player = PlayerORM(
            puuid=riot_account.puuid,
            riot_id=riot_account.gameName,  # camelCase!
            tag_line=riot_account.tagLine,  # Riot-specific naming!
        )

        # Service knows about Riot API structure (TIGHT COUPLING)
        summoner = await self.riot_client.get_summoner(riot_account.puuid)
        player.summoner_name = summoner.name  # More Riot coupling
```

**With ACL** (GOOD):
```python
# Anti-Corruption Layer (Gateway)
class RiotAPIGateway:
    """Translates Riot API semantics to domain language."""

    async def fetch_player_profile(
        self, game_name: str, tag_line: str, platform: str
    ) -> PlayerORM:
        """
        Gateway method expressed in OUR domain terms.

        Hides Riot API details:
        - camelCase → snake_case
        - Riot-specific IDs
        - Multiple API calls coordination
        """
        # Internal: deal with Riot API
        account_dto = await self._client.get_account(game_name, tag_line)
        summoner_dto = await self._client.get_summoner(account_dto.puuid, platform)

        # Transform to OUR domain model
        return PlayerORM(
            puuid=account_dto.puuid,
            riot_id=game_name,  # OUR naming (not gameName)
            tag_line=tag_line,  # OUR naming (not tagLine)
            platform=platform,  # OUR domain concept
            summoner_name=summoner_dto.name,  # Translated
            account_level=summoner_dto.summonerLevel,  # Translated
        )

# Service is clean and domain-focused
class PlayerService:
    async def create_player(self, game_name: str, tag_line: str, platform: str):
        # Service speaks in domain language
        # No knowledge of Riot API structure
        player_orm = await self.riot_gateway.fetch_player_profile(
            game_name, tag_line, platform
        )
        return await self.repo.create(player_orm)
```

**Four-Object Pattern** (Martin Fowler's Refactoring Article):

1. **Connection Object**: Raw HTTP client for external API
2. **Gateway**: Translates external data to domain terms
3. **Coordinator**: Orchestrates multiple gateways if needed
4. **Domain Object**: Your business models

**Benefits**:
- ✅ **Isolation**: External API changes only affect ACL, not domain
- ✅ **Domain Purity**: Domain speaks its own language
- ✅ **Testing**: Mock gateway instead of external API
- ✅ **Flexibility**: Swap external systems without touching domain

**When to Use**:
- ✅ Integrating with third-party APIs (Riot, Stripe, SendGrid)
- ✅ Legacy system integration
- ✅ External system with poor design
- ✅ External system with different naming conventions

---

### 5. DTO (Data Transfer Object) Pattern

**Source**: Martin Fowler, *Patterns of Enterprise Application Architecture*

**Definition**:
> "An object that carries data between processes in order to reduce the number of method calls."

**Original Purpose**: Minimize network round-trips in distributed systems

**Modern Purpose** (in web APIs): Separate API contracts from domain models

**Three Distinct Model Types**:

```python
# 1. External API DTO (Riot API)
class RiotAccountDTO(BaseModel):
    """External API contract - not under our control."""
    puuid: str
    gameName: str      # camelCase from Riot
    tagLine: str       # Riot's naming

# 2. Domain Model (ORM)
class PlayerORM(Base):
    """Internal domain model - database representation."""
    puuid: Mapped[str] = mapped_column(String(78), primary_key=True)
    riot_id: Mapped[str] = mapped_column(String(128))  # Our naming
    tag_line: Mapped[str] = mapped_column(String(32))  # Our naming
    password_hash: Mapped[str] = mapped_column(Text)   # Internal field

    # Business logic
    def is_new_account(self) -> bool:
        return self.account_level < 30

# 3. API Response DTO (Pydantic)
class PlayerPublic(BaseModel):
    """API response contract - client-facing."""
    puuid: str
    riot_id: str
    tag_line: str
    # NO password_hash (security)

    # Computed fields not in database
    smurf_likelihood: float | None = None

    model_config = ConfigDict(from_attributes=True)
```

**Why Three Models?**

| Model Type | Purpose | Changes When... |
|------------|---------|-----------------|
| **External DTO** | Match external API | External API changes |
| **Domain ORM** | Database + business logic | Business rules change |
| **API Response DTO** | Client contract | API version changes |

**Transformation Points**:
```
External API (Riot)
      ↓ (Gateway transforms)
Domain Model (ORM)
      ↓ (Transformer converts)
API Response (DTO)
      ↓ (FastAPI serializes)
JSON to Client
```

**When to Use Different Models**:
- ✅ **Use same model** for simple CRUD if schemas match exactly
- ✅ **Separate Create/Update/Public** even with single table (different fields exposed)
- ✅ **Always separate External DTOs** from domain (Anti-Corruption Layer)

**Example: User Feature**
```python
# Base schema (shared fields)
class UserBase(BaseModel):
    email: EmailStr
    display_name: str

# API Request DTO
class UserCreate(UserBase):
    password: str  # Only in create requests

# Domain Model
class UserORM(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(128))
    password_hash: Mapped[str] = mapped_column(Text)  # Hashed, not raw password

# API Response DTO
class UserPublic(UserBase):
    id: int
    created_at: datetime
    # NO password or password_hash!

    model_config = ConfigDict(from_attributes=True)
```

---

## Decision Matrices

### When to Apply Repository Pattern?

| Scenario | Use Repository? | Reasoning |
|----------|-----------------|-----------|
| **Simple CRUD, single table, 3-5 operations** | ❌ No | Over-engineering, direct queries simpler |
| **Multiple services reuse same queries** | ✅ Yes | Eliminate duplication |
| **Need to mock data access in tests** | ✅ Yes | Enables isolated service testing |
| **Complex queries with joins, aggregations** | ✅ Yes | Centralize complex SQL |
| **Microservice with < 10 DB operations** | ⚠️ Maybe | Consider simplicity vs standardization |
| **Team size > 3 developers** | ✅ Yes | Clear boundaries help coordination |
| **Planning to swap databases** | ✅ Yes | Interface makes migration easier |

### Where Does Logic Belong?

| Logic Type | Domain Model | Service | Repository | Reasoning |
|------------|--------------|---------|------------|-----------|
| **Calculation on entity data** | ✅ | ❌ | ❌ | `player.calculate_win_rate()` |
| **Business rule on single entity** | ✅ | ❌ | ❌ | `player.is_smurf()` |
| **Validation using entity state** | ✅ | ❌ | ❌ | `player.validate_for_tracking()` |
| **Database query** | ❌ | ❌ | ✅ | `repo.find_by_riot_id()` |
| **Orchestration across entities** | ❌ | ✅ | ❌ | Get player + ranks + analyses |
| **Transaction management** | ❌ | ✅ | ❌ | Commit/rollback |
| **External API call** | ❌ | ✅ | ❌ | Call Riot API gateway |
| **Transformation between layers** | ❌ | ✅ | ❌ | ORM → Pydantic DTO |

### Complexity Assessment for Features

Before migrating a feature, assess its complexity:

| Feature Aspect | Low | Medium | High |
|----------------|-----|--------|------|
| **Number of tables** | 1-2 | 3-5 | 6+ |
| **Relationships** | None or simple | 1-2 foreign keys | Multiple joins, M2M |
| **Business logic** | Simple CRUD | Calculations, validations | Complex rules, state machines |
| **External integrations** | None | 1 API | Multiple APIs |
| **Query complexity** | Primary key lookups | Filters, simple joins | CTEs, window functions, aggregations |
| **Recommended patterns** | Direct queries | Repository | Repository + Service + ACL |

**Example Assessment**:

**Settings Feature** (Low Complexity):
- 1 table (system_settings)
- No relationships
- Simple CRUD
- No external APIs
- **Recommendation**: Direct queries in router, skip repository

**Players Feature** (High Complexity):
- 2 tables (players, player_ranks)
- Multiple relationships (matches, analyses)
- Complex business logic (smurf detection)
- External API (Riot)
- Complex queries (fuzzy search, levenshtein distance)
- **Recommendation**: Full enterprise pattern (Repository + Rich Domain + ACL)

---

## Code Templates

### Template 1: ORM Model with Rich Domain Logic

```python
# features/<feature>/orm_models.py
"""SQLAlchemy 2.0 ORM models for <feature> feature."""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base


class <Entity>ORM(Base):
    """
    <Entity> domain model (Rich Domain Model pattern).

    Combines data and behavior:
    - Database fields with type safety
    - Business logic methods
    - Domain validation rules
    """

    __tablename__ = "<table_name>"
    __table_args__ = (
        Index("idx_<table>_<field>", "<field>"),
        {"schema": "<schema_name>"},
    )

    # ========================================================================
    # PRIMARY KEY
    # ========================================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Auto-incrementing primary key"
    )

    # ========================================================================
    # DATA FIELDS
    # ========================================================================

    # String field
    name: Mapped[str] = mapped_column(
        String(128),
        index=True,
        comment="Field description"
    )

    # Optional string field
    description: Mapped[Optional[str]] = mapped_column(
        String(256),
        nullable=True,
        comment="Optional field description"
    )

    # Integer field
    count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Numeric field"
    )

    # Boolean field
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        index=True,
        comment="Active status flag"
    )

    # ========================================================================
    # FOREIGN KEYS
    # ========================================================================

    parent_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("<schema>.<parent_table>.id"),
        index=True,
        comment="Reference to parent entity"
    )

    # ========================================================================
    # TIMESTAMPS
    # ========================================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When this record was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="When this record was last updated"
    )

    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================

    parent: Mapped["ParentORM"] = relationship(back_populates="children")
    children: Mapped[list["ChildORM"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan"
    )

    # ========================================================================
    # RICH DOMAIN MODEL - Business Logic Methods
    # ========================================================================

    def business_calculation(self) -> float:
        """
        Calculate derived value from entity data.

        Business logic on domain data.
        """
        # Implementation here
        return 0.0

    def business_rule(self) -> bool:
        """
        Check business rule.

        Returns:
            True if rule satisfied
        """
        # Implementation here
        return True

    def validate(self) -> list[str]:
        """
        Domain validation rules.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not self.name:
            errors.append("Name is required")

        return errors

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<{self.__class__.__name__}(id={self.id}, name='{self.name}')>"
```

### Template 2: Repository Interface + Implementation

```python
# features/<feature>/repository.py
"""Repository pattern implementation for <feature> feature."""

from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from .orm_models import <Entity>ORM

logger = structlog.get_logger(__name__)


class <Entity>RepositoryInterface(ABC):
    """Interface for <entity> repository."""

    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[<Entity>ORM]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def find_by_criteria(self, **filters) -> list[<Entity>ORM]:
        """Find entities matching criteria."""
        pass

    @abstractmethod
    async def create(self, entity: <Entity>ORM) -> <Entity>ORM:
        """Add new entity."""
        pass

    @abstractmethod
    async def save(self, entity: <Entity>ORM) -> <Entity>ORM:
        """Save existing entity."""
        pass

    @abstractmethod
    async def delete(self, entity: <Entity>ORM) -> None:
        """Remove entity (soft delete)."""
        pass


class SQLAlchemy<Entity>Repository(<Entity>RepositoryInterface):
    """SQLAlchemy implementation of <entity> repository."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db

    async def get_by_id(self, id: int) -> Optional[<Entity>ORM]:
        """Get entity by ID with eager-loaded relationships."""
        stmt = (
            select(<Entity>ORM)
            .options(selectinload(<Entity>ORM.children))
            .where(<Entity>ORM.id == id, <Entity>ORM.is_active == True)
        )

        result = await self.db.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity:
            logger.debug("<entity>_retrieved", id=id)

        return entity

    async def find_by_criteria(self, **filters) -> list[<Entity>ORM]:
        """Find entities matching criteria."""
        stmt = select(<Entity>ORM).where(<Entity>ORM.is_active == True)

        # Apply filters dynamically
        for key, value in filters.items():
            if hasattr(<Entity>ORM, key):
                stmt = stmt.where(getattr(<Entity>ORM, key) == value)

        result = await self.db.execute(stmt)
        entities = list(result.scalars().all())

        logger.debug(
            "<entity>_search",
            filters=filters,
            results_count=len(entities)
        )

        return entities

    async def create(self, entity: <Entity>ORM) -> <Entity>ORM:
        """Create new entity record."""
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)

        logger.info("<entity>_created", id=entity.id)

        return entity

    async def save(self, entity: <Entity>ORM) -> <Entity>ORM:
        """Save existing entity changes."""
        await self.db.commit()
        await self.db.refresh(entity)

        logger.debug("<entity>_saved", id=entity.id)

        return entity

    async def delete(self, entity: <Entity>ORM) -> None:
        """Soft delete entity."""
        entity.is_active = False
        await self.db.commit()

        logger.info("<entity>_deleted", id=entity.id)
```

### Template 3: Pydantic Schemas

```python
# features/<feature>/schemas.py
"""Pydantic schemas for <feature> API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# BASE SCHEMAS - Shared fields
# ============================================================================

class <Entity>Base(BaseModel):
    """Shared fields between requests/responses."""

    name: str = Field(min_length=1, max_length=128, description="Entity name")
    description: Optional[str] = Field(None, max_length=256, description="Optional description")


# ============================================================================
# REQUEST SCHEMAS - API inputs
# ============================================================================

class <Entity>Create(<Entity>Base):
    """Schema for creating entity."""
    pass  # Inherits from Base


class <Entity>Update(BaseModel):
    """Schema for updating entity (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=256)
    is_active: Optional[bool] = None


# ============================================================================
# RESPONSE SCHEMAS - API outputs
# ============================================================================

class <Entity>Public(<Entity>Base):
    """Schema for entity API response."""

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Computed fields from domain logic
    computed_value: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class <Entity>Detail(<Entity>Public):
    """Detailed entity response with relationships."""

    children: list["ChildPublic"] = []


# ============================================================================
# LIST RESPONSES
# ============================================================================

class <Entity>ListResponse(BaseModel):
    """Paginated list of entities."""

    entities: list[<Entity>Public]
    total: int
    page: int
    size: int
    pages: int
```

### Template 4: Service Layer

```python
# features/<feature>/service.py
"""Service layer for <feature> - thin orchestration only."""

from typing import Optional
import structlog

from .repository import <Entity>RepositoryInterface
from .orm_models import <Entity>ORM
from .schemas import <Entity>Public, <Entity>Create, <Entity>Update
from .transformers import <Entity>Transformer
from .exceptions import <Entity>NotFoundError, ValidationError

logger = structlog.get_logger(__name__)


class <Entity>Service:
    """
    <Entity> service - orchestrates operations across layers.

    Responsibilities:
    - Coordinate repository and domain models
    - Handle transactions
    - Transform between layers

    Does NOT contain:
    - Database queries (in repository)
    - Business logic (in domain models)
    """

    def __init__(self, repository: <Entity>RepositoryInterface):
        """Initialize service with dependencies."""
        self.repo = repository

    async def get_entity(self, id: int) -> <Entity>Public:
        """
        Get entity by ID.

        Args:
            id: Entity identifier

        Returns:
            Entity API response

        Raises:
            <Entity>NotFoundError: If entity doesn't exist
        """
        # Delegate data access to repository
        entity_orm = await self.repo.get_by_id(id)

        if not entity_orm:
            raise <Entity>NotFoundError(f"Entity not found: {id}")

        # Transform ORM → API response (includes computed fields)
        return <Entity>Transformer.to_public_schema(entity_orm)

    async def create_entity(self, entity_data: <Entity>Create) -> <Entity>Public:
        """
        Create new entity.

        Args:
            entity_data: Entity creation data

        Returns:
            Created entity API response
        """
        # Create domain model from API request
        entity_orm = <Entity>ORM(
            name=entity_data.name,
            description=entity_data.description,
        )

        # Delegate validation to domain model
        validation_errors = entity_orm.validate()
        if validation_errors:
            raise ValidationError(validation_errors)

        # Delegate persistence to repository
        created_entity = await self.repo.create(entity_orm)

        logger.info("<entity>_created", id=created_entity.id)

        # Transform ORM → API response
        return <Entity>Transformer.to_public_schema(created_entity)

    async def update_entity(
        self, id: int, entity_data: <Entity>Update
    ) -> <Entity>Public:
        """
        Update existing entity.

        Args:
            id: Entity identifier
            entity_data: Update data

        Returns:
            Updated entity API response

        Raises:
            <Entity>NotFoundError: If entity doesn't exist
        """
        # Delegate data access to repository
        entity_orm = await self.repo.get_by_id(id)

        if not entity_orm:
            raise <Entity>NotFoundError(f"Entity not found: {id}")

        # Apply updates (only provided fields)
        update_data = entity_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(entity_orm, key, value)

        # Delegate validation to domain model
        validation_errors = entity_orm.validate()
        if validation_errors:
            raise ValidationError(validation_errors)

        # Delegate persistence to repository
        updated_entity = await self.repo.save(entity_orm)

        logger.info("<entity>_updated", id=id)

        # Transform ORM → API response
        return <Entity>Transformer.to_public_schema(updated_entity)

    async def delete_entity(self, id: int) -> None:
        """
        Delete entity.

        Args:
            id: Entity identifier

        Raises:
            <Entity>NotFoundError: If entity doesn't exist
        """
        # Delegate data access to repository
        entity_orm = await self.repo.get_by_id(id)

        if not entity_orm:
            raise <Entity>NotFoundError(f"Entity not found: {id}")

        # Delegate deletion to repository
        await self.repo.delete(entity_orm)

        logger.info("<entity>_deleted", id=id)
```

### Template 5: Transformer

```python
# features/<feature>/transformers.py
"""Transformers for converting between layers."""

from .orm_models import <Entity>ORM
from .schemas import <Entity>Public


class <Entity>Transformer:
    """Transforms between ORM and Pydantic schemas."""

    @staticmethod
    def to_public_schema(entity_orm: <Entity>ORM) -> <Entity>Public:
        """
        Transform domain ORM to API response DTO.

        Args:
            entity_orm: Domain model from database

        Returns:
            Pydantic schema for API response
        """
        return <Entity>Public(
            id=entity_orm.id,
            name=entity_orm.name,
            description=entity_orm.description,
            is_active=entity_orm.is_active,
            created_at=entity_orm.created_at,
            updated_at=entity_orm.updated_at,
            # Computed fields using domain logic
            computed_value=entity_orm.business_calculation(),
        )
```

### Template 6: Router

```python
# features/<feature>/router.py
"""FastAPI routes for <feature>."""

from fastapi import APIRouter, Depends, HTTPException, Query
from .dependencies import get_<entity>_service
from .service import <Entity>Service
from .schemas import <Entity>Public, <Entity>Create, <Entity>Update
from .exceptions import <Entity>NotFoundError, ValidationError

router = APIRouter(prefix="/<entities>", tags=["<entities>"])


@router.get("/{id}", response_model=<Entity>Public)
async def get_entity(
    id: int,
    service: <Entity>Service = Depends(get_<entity>_service),
):
    """Get entity by ID."""
    try:
        return await service.get_entity(id)
    except <Entity>NotFoundError:
        raise HTTPException(status_code=404, detail="Entity not found")


@router.post("", response_model=<Entity>Public, status_code=201)
async def create_entity(
    entity_data: <Entity>Create,
    service: <Entity>Service = Depends(get_<entity>_service),
):
    """Create new entity."""
    try:
        return await service.create_entity(entity_data)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.patch("/{id}", response_model=<Entity>Public)
async def update_entity(
    id: int,
    entity_data: <Entity>Update,
    service: <Entity>Service = Depends(get_<entity>_service),
):
    """Update existing entity."""
    try:
        return await service.update_entity(id, entity_data)
    except <Entity>NotFoundError:
        raise HTTPException(status_code=404, detail="Entity not found")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{id}", status_code=204)
async def delete_entity(
    id: int,
    service: <Entity>Service = Depends(get_<entity>_service),
):
    """Delete entity."""
    try:
        await service.delete_entity(id)
    except <Entity>NotFoundError:
        raise HTTPException(status_code=404, detail="Entity not found")
```

### Template 7: Dependencies

```python
# features/<feature>/dependencies.py
"""Dependency injection for <feature>."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from .repository import <Entity>RepositoryInterface, SQLAlchemy<Entity>Repository
from .service import <Entity>Service


def get_<entity>_repository(
    db: AsyncSession = Depends(get_db)
) -> <Entity>RepositoryInterface:
    """Provide <entity> repository."""
    return SQLAlchemy<Entity>Repository(db)


def get_<entity>_service(
    repository: <Entity>RepositoryInterface = Depends(get_<entity>_repository),
) -> <Entity>Service:
    """Provide <entity> service."""
    return <Entity>Service(repository)
```

---

## Type Safety Configuration

### pyproject.toml Configuration

```toml
# pyproject.toml

[project.dependencies]
sqlalchemy = "^2.0.0"
pydantic = "^2.0.0"
fastapi = "^0.115.0"

[tool.mypy]
python_version = "3.11"
plugins = ["sqlalchemy.ext.mypy.plugin", "pydantic.mypy"]

# Strict mode
strict = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_return_any = true
warn_unreachable = true
disallow_untyped_defs = true
disallow_untyped_calls = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true

# SQLAlchemy specific
[tool.sqlalchemy.mypy]
mypy_plugin_config = "warn_on_backref"

# Pydantic specific
[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true

# Per-module overrides
[tool.mypy.overrides]
module = "alembic.*"
ignore_errors = true

[tool.pyright]
typeCheckingMode = "strict"
reportMissingTypeStubs = false
reportUnknownMemberType = false
reportUnknownVariableType = false
reportUnknownArgumentType = false
pythonVersion = "3.11"
```

### Running Type Checkers

```bash
# Run mypy
mypy backend/app/

# Run pyright
pyright backend/app/

# Run both in CI
mypy backend/app/ && pyright backend/app/
```

### Common Type Issues and Solutions

**Issue 1: Optional fields without default**
```python
# ❌ Wrong
class PlayerORM(Base):
    summoner_name: Mapped[Optional[str]] = mapped_column(String(32))

# ✅ Correct
class PlayerORM(Base):
    summoner_name: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
```

**Issue 2: Relationship types**
```python
# ❌ Wrong (no type hint)
class PlayerORM(Base):
    ranks = relationship("PlayerRankORM")

# ✅ Correct (with Mapped type)
class PlayerORM(Base):
    ranks: Mapped[list["PlayerRankORM"]] = relationship(back_populates="player")
```

**Issue 3: Forward references**
```python
# Use TYPE_CHECKING for circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.features.matches import MatchORM

class PlayerORM(Base):
    matches: Mapped[list["MatchORM"]] = relationship(back_populates="players")
```

---

## Best Practices

### 1. Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| **ORM Model** | `<Entity>ORM` | `PlayerORM`, `MatchORM` |
| **Repository Interface** | `<Entity>RepositoryInterface` | `PlayerRepositoryInterface` |
| **Repository Impl** | `SQLAlchemy<Entity>Repository` | `SQLAlchemyPlayerRepository` |
| **Service** | `<Entity>Service` | `PlayerService` |
| **Pydantic Create** | `<Entity>Create` | `PlayerCreate` |
| **Pydantic Update** | `<Entity>Update` | `PlayerUpdate` |
| **Pydantic Response** | `<Entity>Public` | `PlayerPublic` |
| **Transformer** | `<Entity>Transformer` | `PlayerTransformer` |
| **Exception** | `<Entity><Error>Error` | `PlayerNotFoundError` |

### 2. File Organization

**Keep features self-contained**:
```
features/<feature>/
├── __init__.py           # Public API exports only
├── orm_models.py         # ORM models (database)
├── schemas.py            # Pydantic schemas (API)
├── repository.py         # Data access layer
├── service.py            # Orchestration layer
├── transformers.py       # Layer transformations
├── router.py             # FastAPI endpoints
├── dependencies.py       # Dependency injection
├── exceptions.py         # Feature-specific exceptions
└── README.md             # Feature documentation
```

### 3. Import Rules

**Public API Pattern** (`__init__.py`):
```python
"""<Feature> feature - enterprise architecture.

Public API exports only. Internal modules should not be imported directly.
"""

from .orm_models import <Entity>ORM
from .schemas import <Entity>Create, <Entity>Update, <Entity>Public
from .repository import <Entity>RepositoryInterface, SQLAlchemy<Entity>Repository
from .service import <Entity>Service
from .router import router as <feature>_router

__all__ = [
    # Domain models
    "<Entity>ORM",
    # API schemas
    "<Entity>Create",
    "<Entity>Update",
    "<Entity>Public",
    # Repository
    "<Entity>RepositoryInterface",
    "SQLAlchemy<Entity>Repository",
    # Service
    "<Entity>Service",
    # Router
    "<feature>_router",
]
```

**Import from public API**:
```python
# ✅ Good: Import from feature package
from app.features.players import PlayerORM, PlayerService, PlayerPublic

# ❌ Bad: Import from internal modules
from app.features.players.orm_models import PlayerORM
from app.features.players.service import PlayerService
```

### 4. Dependency Direction

```
┌─────────────────┐
│   Router (API)  │
└────────┬────────┘
         │ depends on
         ▼
┌─────────────────┐
│    Service      │
└────────┬────────┘
         │ depends on
         ▼
┌─────────────────┐
│   Repository    │
└────────┬────────┘
         │ depends on
         ▼
┌─────────────────┐
│   ORM Models    │
└────────┬────────┘
         │ depends on
         ▼
┌─────────────────┐
│    Database     │
└─────────────────┘
```

**Rule**: NEVER reverse dependency direction

### 5. Logging Strategy

```python
import structlog

logger = structlog.get_logger(__name__)

# Use structured logging with context keys
logger.info(
    "player_created",           # Event name (snake_case)
    puuid=player.puuid,         # Context keys
    riot_id=player.riot_id,
    platform=player.platform
)

# Log levels:
# - debug: Detailed info for debugging
# - info: Normal operations (create, update, delete)
# - warning: Unexpected but handled situations
# - error: Errors that need attention
# - critical: System failures
```

### 6. Error Handling

**Create feature-specific exceptions**:
```python
# features/<feature>/exceptions.py
class <Feature>Error(Exception):
    """Base exception for <feature> feature."""
    pass

class <Entity>NotFoundError(<Feature>Error):
    """Entity not found in database."""
    pass

class ValidationError(<Feature>Error):
    """Entity validation failed."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(", ".join(errors))
```

**Handle in router**:
```python
@router.get("/{id}")
async def get_entity(id: int, service: Service = Depends(get_service)):
    try:
        return await service.get_entity(id)
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail="Entity not found")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
```

---

## Common Pitfalls

### Pitfall 1: Anemic Domain Models

**❌ Wrong**:
```python
# All behavior in service
class Player:
    puuid: str
    wins: int
    losses: int

class PlayerService:
    def calculate_win_rate(self, player: Player) -> float:
        total = player.wins + player.losses
        return (player.wins / total * 100) if total > 0 else 0.0
```

**✅ Correct**:
```python
# Behavior in domain model
class Player:
    puuid: str
    wins: int
    losses: int

    def calculate_win_rate(self) -> float:
        total = self.wins + self.losses
        return (self.wins / total * 100) if total > 0 else 0.0
```

### Pitfall 2: Repository with Business Logic

**❌ Wrong**:
```python
class PlayerRepository:
    async def get_smurfs(self) -> list[PlayerORM]:
        # Business logic in repository!
        stmt = select(PlayerORM).where(
            PlayerORM.account_level < 30,
            PlayerORM.wins / (PlayerORM.wins + PlayerORM.losses) > 0.65
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
```

**✅ Correct**:
```python
# Repository: data access only
class PlayerRepository:
    async def get_all_active(self) -> list[PlayerORM]:
        stmt = select(PlayerORM).where(PlayerORM.is_active == True)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

# Service: orchestration
class PlayerService:
    async def get_smurfs(self) -> list[PlayerPublic]:
        players = await self.repo.get_all_active()
        # Domain model: business logic
        smurfs = [p for p in players if p.is_smurf()]
        return [self.transformer.to_public(p) for p in smurfs]
```

### Pitfall 3: Fat Service Layer

**❌ Wrong**:
```python
class PlayerService:
    # Service doing EVERYTHING
    async def track_player(self, puuid: str):
        # Query (should be in repository)
        result = await self.db.execute(
            select(Player).where(Player.puuid == puuid)
        )
        player = result.scalar_one_or_none()

        # Business logic (should be in model)
        if not player.riot_id or not player.tag_line:
            raise ValueError("Cannot track")

        # State change (should be in model)
        player.is_tracked = True

        # Persistence (should be in repository)
        await self.db.commit()
```

**✅ Correct**:
```python
class PlayerService:
    # Service orchestrates only
    async def track_player(self, puuid: str):
        # Repository: data access
        player = await self.repo.get_by_puuid(puuid)

        # Domain model: validation
        errors = player.validate_for_tracking()
        if errors:
            raise ValidationError(errors)

        # Domain model: state change
        player.mark_as_tracked()

        # Repository: persistence
        await self.repo.save(player)
```

### Pitfall 4: Leaking External API Semantics

**❌ Wrong**:
```python
# Service knows about Riot API structure
class PlayerService:
    async def create_player(self, name: str, tag: str):
        # Riot API returns camelCase
        riot_data = await self.riot_client.get_account(name, tag)

        # Service deals with Riot-specific fields
        player = PlayerORM(
            puuid=riot_data.puuid,
            riot_id=riot_data.gameName,  # camelCase leaks in!
            tag_line=riot_data.tagLine    # Riot semantics!
        )
```

**✅ Correct**:
```python
# Gateway (ACL) hides Riot API
class RiotAPIGateway:
    async def fetch_player_profile(
        self, name: str, tag: str, platform: str
    ) -> PlayerORM:
        # Internal: deal with Riot API
        riot_data = await self.client.get_account(name, tag)

        # Transform to domain model
        return PlayerORM(
            puuid=riot_data.puuid,
            riot_id=name,       # OUR naming
            tag_line=tag,       # OUR naming
            platform=platform   # OUR concept
        )

# Service is clean
class PlayerService:
    async def create_player(self, name: str, tag: str, platform: str):
        # Service doesn't know about Riot API
        player_orm = await self.riot_gateway.fetch_player_profile(name, tag, platform)
        return await self.repo.create(player_orm)
```

### Pitfall 5: N+1 Query Problem

**❌ Wrong**:
```python
# Repository doesn't eager load
class PlayerRepository:
    async def get_by_id(self, id: int) -> PlayerORM:
        stmt = select(PlayerORM).where(PlayerORM.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

# Service triggers N+1 queries
async def get_players_with_ranks():
    players = await repo.get_all()
    # Each player.ranks access triggers a query!
    return [{"player": p, "rank_count": len(p.ranks)} for p in players]
```

**✅ Correct**:
```python
# Repository eager loads relationships
class PlayerRepository:
    async def get_by_id(self, id: int) -> PlayerORM:
        stmt = (
            select(PlayerORM)
            .options(selectinload(PlayerORM.ranks))  # Eager load!
            .where(PlayerORM.id == id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

# Service: no N+1 issue
async def get_players_with_ranks():
    players = await repo.get_all()
    # No extra queries - ranks already loaded
    return [{"player": p, "rank_count": len(p.ranks)} for p in players]
```

---

## Feature Migration Checklist

Use this checklist when migrating each feature to enterprise patterns.

### Pre-Migration

- [ ] **Assess Complexity**
  - [ ] Count tables (1-2 = low, 3-5 = medium, 6+ = high)
  - [ ] Assess business logic complexity
  - [ ] Check external API integrations
  - [ ] Determine if patterns needed (use decision matrix)

- [ ] **Review Current Code**
  - [ ] Read existing models, services, routers
  - [ ] Identify business logic scattered in service
  - [ ] Note database query patterns
  - [ ] List external API calls

- [ ] **Plan Approach**
  - [ ] Decide which patterns to apply
  - [ ] Estimate effort (use players feature as benchmark)
  - [ ] Create migration branch

### Implementation

- [ ] **Phase 1: ORM Models** (2-3 hours)
  - [ ] Create `orm_models.py` with SQLAlchemy 2.0 `Mapped` types
  - [ ] Add business logic methods to models
  - [ ] Add validation methods
  - [ ] Add `__repr__` for debugging
  - [ ] Test domain logic (no database needed)

- [ ] **Phase 2: Repository Layer** (3-4 hours)
  - [ ] Create repository interface
  - [ ] Implement SQLAlchemy repository
  - [ ] Move all queries from service to repository
  - [ ] Configure eager loading for relationships
  - [ ] Test repository with test database

- [ ] **Phase 3: Service Refactoring** (4-5 hours)
  - [ ] Create transformer for DTO conversions
  - [ ] Refactor service to use repository
  - [ ] Remove business logic from service (move to models)
  - [ ] Remove database queries from service (move to repository)
  - [ ] Test service with mocked repository

- [ ] **Phase 4: Router Updates** (1-2 hours)
  - [ ] Update dependency injection
  - [ ] Verify router endpoints still work
  - [ ] Add integration tests

- [ ] **Phase 5: Testing** (4-5 hours)
  - [ ] Write domain model tests
  - [ ] Write repository tests
  - [ ] Write service tests (with mocks)
  - [ ] Write integration tests
  - [ ] Achieve target coverage (domain 100%, repository 95%, service 90%)

- [ ] **Phase 6: Documentation** (1 hour)
  - [ ] Update `__init__.py` exports
  - [ ] Update README.md
  - [ ] Add code comments
  - [ ] Document patterns used

### Validation

- [ ] **Type Safety**
  - [ ] mypy passes with strict mode
  - [ ] pyright passes with strict mode
  - [ ] No `type: ignore` comments added

- [ ] **Tests Pass**
  - [ ] All new tests pass
  - [ ] All existing tests pass
  - [ ] Coverage targets met

- [ ] **No Regressions**
  - [ ] All API endpoints work
  - [ ] Same response shapes
  - [ ] No performance degradation

- [ ] **Code Quality**
  - [ ] Patterns applied correctly
  - [ ] Clear layer separation
  - [ ] SOLID principles followed

### Post-Migration

- [ ] **Review and Iterate**
  - [ ] Code review with team
  - [ ] Adjust based on feedback
  - [ ] Update patterns guide if needed

- [ ] **Merge and Deploy**
  - [ ] Merge to main branch
  - [ ] Deploy to staging
  - [ ] Monitor for issues
  - [ ] Deploy to production

- [ ] **Document Learnings**
  - [ ] Note what worked well
  - [ ] Note what was difficult
  - [ ] Update this guide with insights

---

## Summary

This guide provides reusable templates and patterns for implementing enterprise-grade architecture in any feature. Key takeaways:

1. **Use Repository Pattern** for data access abstraction
2. **Use Rich Domain Models** to keep business logic with data
3. **Use Anti-Corruption Layer** to protect domain from external APIs
4. **Use DTO Pattern** to separate API contracts from domain models
5. **Keep Service Layer Thin** - orchestration only, delegate everything else

Apply these patterns incrementally, starting with complex features (players, matches) and leaving simple features (settings) as direct queries.

**See Also**:
- `docs/plans/players-feature-enterprise-patterns.md` - Complete implementation example
- Martin Fowler's *Patterns of Enterprise Application Architecture*
- FastAPI documentation
- SQLAlchemy 2.0 documentation
