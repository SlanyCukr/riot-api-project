# SQLModel and Alembic Integration Documentation

**Retrieved**: 2025-10-27

## Overview

This document contains comprehensive documentation on integrating SQLModel with Alembic for database migrations, including best practices for configuration, autogenerate setup, and troubleshooting common issues.

---

## Table of Contents

1. [SQLModel Metadata Basics](#sqlmodel-metadata-basics)
2. [Alembic env.py Configuration](#alembic-envpy-configuration)
3. [Target Metadata Setup](#target-metadata-setup)
4. [Autogenerate Configuration](#autogenerate-configuration)
5. [Known Issues and Solutions](#known-issues-and-solutions)
6. [Migration Best Practices](#migration-best-practices)

---

## SQLModel Metadata Basics

### Understanding SQLModel.metadata

SQLModel uses SQLAlchemy's MetaData under the hood. When you define models with `table=True`, they are automatically registered in `SQLModel.metadata`.

```python
from sqlmodel import Field, SQLModel

class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    secret_name: str
    age: int | None = Field(default=None, index=True)
```

### Creating Tables (Development Only)

**IMPORTANT**: In production, NEVER use `create_all()`. Always use Alembic migrations.

```python
from sqlmodel import create_engine

engine = create_engine("sqlite:///database.db")

# Only for quick prototyping - NOT for production
SQLModel.metadata.create_all(engine)
```

### Working with Relationships

SQLModel supports both single and many-to-many relationships:

```python
from sqlmodel import Field, Relationship, SQLModel

class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    headquarters: str

    heroes: list["Hero"] = Relationship(back_populates="team")

class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    secret_name: str
    age: int | None = Field(default=None, index=True)

    team_id: int | None = Field(default=None, foreign_key="team.id")
    team: Team | None = Relationship(back_populates="heroes")
```

---

## Alembic env.py Configuration

### Basic Configuration for SQLModel

The key to integrating SQLModel with Alembic is properly setting `target_metadata` in your `env.py`:

```python
from sqlmodel import SQLModel
from app.core.models import *  # Import all your models

# Set target_metadata to SQLModel.metadata
target_metadata = SQLModel.metadata
```

### Complete env.py Template

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import SQLModel and all your models
from sqlmodel import SQLModel
from app.core.models import *
from app.features.players.models import *
from app.features.matches.models import *
# ... import all feature models

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target_metadata for autogenerate support
target_metadata = SQLModel.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Optional: Enable type comparison for better autogenerate
            compare_type=True,
            # Optional: Compare server defaults
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

## Target Metadata Setup

### Single Metadata Object

For most applications using SQLModel, you have a single metadata object:

```python
from sqlmodel import SQLModel

# In env.py
target_metadata = SQLModel.metadata
```

### Multiple Metadata Objects

If you have multiple metadata collections (rare with SQLModel):

```python
from app.models import Base1, Base2

target_metadata = [Base1.metadata, Base2.metadata]
```

Alembic will consult these in order during autogenerate.

### Ensuring All Models Are Imported

**CRITICAL**: Alembic can only detect models that are imported before `target_metadata` is set.

```python
# env.py - Import ALL models
from sqlmodel import SQLModel

# Core models
from app.core.models import *

# Feature models
from app.features.players.models import *
from app.features.matches.models import *
from app.features.auth.models import *
from app.features.jobs.models import *
from app.features.settings.models import *

# NOW set target_metadata
target_metadata = SQLModel.metadata
```

---

## Autogenerate Configuration

### Basic Autogenerate Command

```bash
alembic revision --autogenerate -m "description of change"
```

### Enhanced Autogenerate with Options

Configure in `env.py` for better autogenerate detection:

```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    # Compare column types (detects type changes)
    compare_type=True,
    # Compare server defaults
    compare_server_default=True,
    # Include schemas (for multi-schema setups)
    include_schemas=True,
    # Custom object filtering
    include_object=include_object,
    include_name=include_name,
)
```

### Filtering Objects with include_object

Control which database objects are included in autogenerate:

```python
def include_object(object, name, type_, reflected, compare_to):
    """
    Filter objects during autogenerate.

    Args:
        object: The schema object (Table, Column, etc.)
        name: The name of the object
        type_: Type of object ('table', 'column', 'index', etc.)
        reflected: True if object exists in database
        compare_to: The corresponding object in target_metadata (None if not found)
    """
    # Skip tables managed by external libraries (e.g., APScheduler)
    if type_ == "table" and name.startswith("apscheduler_"):
        return False

    # Skip temporary tables
    if type_ == "table" and name.startswith("temp_"):
        return False

    # Prevent DROP TABLE for tables not in metadata but in database
    if type_ == "table" and reflected and compare_to is None:
        return False

    # Skip columns with skip_autogenerate flag
    if (type_ == "column" and
        not reflected and
        hasattr(object, 'info') and
        object.info.get("skip_autogenerate", False)):
        return False

    return True

# In run_migrations_online():
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    include_object=include_object,
)
```

### Filtering Names with include_name

Filter objects by name patterns:

```python
def include_name(name, type_, parent_names):
    """
    Filter objects by name during autogenerate.

    Args:
        name: Name of the object
        type_: Type ('schema', 'table', 'column', etc.)
        parent_names: Dict with parent object names
    """
    # Skip information_schema
    if type_ == "schema" and name == "information_schema":
        return False

    # Only include specific schemas
    if type_ == "schema":
        return name in [None, "public", "my_schema"]

    # For tables, use schema_qualified_table_name
    if type_ == "table":
        return (
            parent_names.get("schema_qualified_table_name") in
            target_metadata.tables
        )

    return True

context.configure(
    connection=connection,
    target_metadata=target_metadata,
    include_name=include_name,
)
```

---

## Known Issues and Solutions

### Issue 1: Autogenerate Detects All Tables as New

**Symptom**: After migrating from SQLAlchemy `Base.metadata` to `SQLModel.metadata`, autogenerate thinks all existing tables are new.

**Root Cause**:
- Models are not imported before `target_metadata` is set
- Old migrations reference `Base.metadata` instead of `SQLModel.metadata`
- Metadata object was changed but existing migrations weren't updated

**Solutions**:

1. **Ensure All Models Are Imported**:
```python
# env.py
from sqlmodel import SQLModel

# Import ALL models - this registers them with SQLModel.metadata
from app.core.models import *
from app.features.players.models import *
# ... all other features

target_metadata = SQLModel.metadata
```

2. **Update Existing Migrations** (if migrating from Base to SQLModel):
```python
# In each old migration file that references Base
# OLD:
# from app.core.models import Base
# target_metadata = Base.metadata

# NEW:
from sqlmodel import SQLModel
target_metadata = SQLModel.metadata
```

3. **Create a Baseline Migration**:
If you have many old migrations, create a fresh baseline:
```bash
# Mark current database state as baseline
alembic stamp head

# Create new migration
alembic revision --autogenerate -m "baseline after SQLModel migration"
```

### Issue 2: Foreign Keys Not Detected Correctly

**Symptom**: Autogenerate tries to recreate existing foreign keys or doesn't detect FK changes.

**Solution**: Ensure foreign key relationships use correct database-side column names:

```python
class Hero(SQLModel, table=True):
    team_id: int | None = Field(default=None, foreign_key="team.id")
    # Use database table name, not Python class name
    # Correct: "team.id"
    # Incorrect: "Team.id"
```

### Issue 3: Custom Types Not Rendered Correctly

**Symptom**: Autogenerate doesn't properly render custom SQLAlchemy types (Enums, Arrays, etc.).

**Solution**: Configure custom type rendering in env.py:

```python
from sqlalchemy import Enum
from app.core.enums import MyEnum

def render_item(type_, obj, autogen_context):
    """Custom rendering for migration directives."""
    if type_ == "type" and isinstance(obj, Enum):
        # Render Enums properly
        return f"sa.Enum({obj.name!r}, ...)"

    # Return False to use default rendering
    return False

context.configure(
    connection=connection,
    target_metadata=target_metadata,
    render_item=render_item,
)
```

### Issue 4: Schema-Specific Issues (PostgreSQL)

**Symptom**: Tables in non-public schemas not detected correctly.

**Solution**: Enable schema support and configure properly:

```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    include_schemas=True,
    include_name=include_name,  # Use include_name to filter schemas
)
```

### Issue 5: Tables Managed by External Libraries

**Symptom**: Autogenerate tries to create/modify tables managed by APScheduler, Alembic, etc.

**Solution**: Use `include_object` to exclude these tables:

```python
def include_object(object, name, type_, reflected, compare_to):
    # Skip APScheduler tables
    if type_ == "table" and name.startswith("apscheduler_"):
        return False

    # Skip Alembic version table
    if type_ == "table" and name == "alembic_version":
        return False

    return True
```

---

## Migration Best Practices

### 1. Always Review Autogenerated Migrations

Autogenerate is a starting point, not the final solution:

```bash
# After generating
alembic revision --autogenerate -m "description"

# ALWAYS review the generated file in alembic/versions/
# Check for:
# - Incorrect DROP statements
# - Missing data migrations
# - Type changes that need data conversion
```

### 2. Import All Models Early

Create a central import location:

```python
# app/core/models.py or app/models/__init__.py
from sqlmodel import SQLModel

# Import all models here
from app.features.players.models import *
from app.features.matches.models import *
from app.features.auth.models import *

# This ensures all models are registered with SQLModel.metadata
```

Then in `env.py`:
```python
from app.core.models import *
target_metadata = SQLModel.metadata
```

### 3. Use Descriptive Migration Messages

```bash
# Bad
alembic revision --autogenerate -m "update"

# Good
alembic revision --autogenerate -m "add email column to users table"
```

### 4. Test Migrations Locally

```bash
# Test upgrade
alembic upgrade head

# Test downgrade
alembic downgrade -1

# Test re-upgrade
alembic upgrade head
```

### 5. Handle Data Migrations Explicitly

Autogenerate only handles schema. For data changes:

```python
# In migration file
def upgrade():
    # Schema change (autogenerated)
    op.add_column('users', sa.Column('status', sa.String(20)))

    # Data migration (manual)
    connection = op.get_bind()
    connection.execute(
        text("UPDATE users SET status = 'active' WHERE active = true")
    )

def downgrade():
    # Reverse data migration first
    connection = op.get_bind()
    connection.execute(
        text("UPDATE users SET active = (status = 'active')")
    )

    # Then schema change
    op.drop_column('users', 'status')
```

### 6. Use Batch Operations for SQLite

SQLite has limited ALTER TABLE support. Use batch operations:

```python
# In env.py
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    render_as_batch=True,  # For SQLite
)
```

This generates migrations like:
```python
def upgrade():
    with op.batch_alter_table('address', schema=None) as batch_op:
        batch_op.add_column(sa.Column('street', sa.String(length=50)))
```

### 7. Configure Post-Write Hooks for Code Quality

Format generated migrations automatically:

```ini
# alembic.ini
[post_write_hooks]
hooks = black

black.type = console_scripts
black.entrypoint = black
black.options = -l 79 REVISION_SCRIPT_FILENAME
```

Or in `pyproject.toml`:
```toml
[[tool.alembic.post_write_hooks]]
name = "black"
type = "console_scripts"
entrypoint = "black"
options = "-l 79 REVISION_SCRIPT_FILENAME"
```

---

## Troubleshooting Checklist

When autogenerate isn't working correctly:

- [ ] Are all models imported in `env.py` before `target_metadata` is set?
- [ ] Is `target_metadata = SQLModel.metadata` set correctly?
- [ ] Have you reviewed the generated migration file manually?
- [ ] Are foreign key references using database table names (lowercase)?
- [ ] Are you excluding tables managed by external libraries?
- [ ] Have you tested both upgrade and downgrade?
- [ ] Are you using `render_as_batch=True` for SQLite?
- [ ] Have you checked for custom types that need special rendering?

---

## Additional Resources

- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Metadata](https://docs.sqlalchemy.org/en/20/core/metadata.html)
- [Alembic Autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)

---

## Example: Complete Migration from SQLAlchemy Base to SQLModel

If you're migrating an existing codebase:

### Step 1: Update Model Definitions

```python
# Before (SQLAlchemy)
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))

# After (SQLModel)
from sqlmodel import Field, SQLModel

class User(SQLModel, table=True):
    __tablename__ = "users"  # Optional: SQLModel infers from class name
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=50)
```

### Step 2: Update env.py

```python
# Before
from app.database import Base
target_metadata = Base.metadata

# After
from sqlmodel import SQLModel
from app.models import *  # Import all models
target_metadata = SQLModel.metadata
```

### Step 3: Create Verification Migration

```bash
alembic revision --autogenerate -m "verify SQLModel migration - should be empty"
```

This should generate an empty migration if everything is correct. If it detects changes, investigate why.

### Step 4: Update Old Migrations (Optional but Recommended)

For consistency, update the target_metadata reference in old migration files:

```python
# In old migration files
from sqlmodel import SQLModel
target_metadata = SQLModel.metadata
```

This ensures all migrations reference the same metadata object.

---

**Document End**
