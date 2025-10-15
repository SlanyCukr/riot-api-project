"""Database models package initialization."""

from typing import Optional
from typing_extensions import Annotated
from decimal import Decimal
from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    Numeric,
    BigInteger,
    DateTime as SQLDateTime,
    ForeignKey,
    MetaData,
)
from sqlalchemy.orm import DeclarativeBase, mapped_column


# Create a base class for declarative models using SQLAlchemy 2.0 style
# Use a custom naming convention for constraints and indexes
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)

# Type annotation map for Python → SQL type mapping
type_annotation_map = {
    str: String(),
    int: Integer(),
    bool: Boolean(),
    float: Numeric(),
    Decimal: Numeric(),
    datetime: SQLDateTime(),
    Optional[str]: String(),
    Optional[int]: Integer(),
    Optional[bool]: Boolean(),
    Optional[float]: Numeric(),
    Optional[Decimal]: Numeric(),
    Optional[datetime]: SQLDateTime(),
}


class Base(DeclarativeBase):
    """Base class for all database models using SQLAlchemy 2.0."""

    __abstract__ = True

    metadata = metadata
    type_annotation_map = type_annotation_map


# Common Annotated types for repeated patterns
PrimaryKeyStr = Annotated[str, mapped_column(primary_key=True)]
PrimaryKeyInt = Annotated[int, mapped_column(primary_key=True)]

RequiredString = Annotated[str, mapped_column(nullable=False)]
OptionalString = Annotated[Optional[str], mapped_column()]

RequiredInt = Annotated[int, mapped_column(nullable=False)]
OptionalInt = Annotated[Optional[int], mapped_column()]

RequiredBool = Annotated[bool, mapped_column(nullable=False)]
OptionalBool = Annotated[Optional[bool], mapped_column()]

RequiredDecimal = Annotated[Decimal, mapped_column(nullable=False)]
OptionalDecimal = Annotated[Optional[Decimal], mapped_column()]

RequiredBigInt = Annotated[int, mapped_column(BigInteger, nullable=False)]
OptionalBigInt = Annotated[Optional[int], mapped_column(BigInteger)]

RequiredDateTime = Annotated[datetime, mapped_column(nullable=False)]
OptionalDateTime = Annotated[Optional[datetime], mapped_column()]

# Common field patterns with specific constraints
PUUIDField = Annotated[str, mapped_column(String(78), primary_key=True, index=True)]
PUUIDForeignKey = Annotated[
    str, mapped_column(String(78), ForeignKey("players.puuid", ondelete="CASCADE"))
]
MatchIDField = Annotated[str, mapped_column(String(64), primary_key=True)]
MatchIDForeignKey = Annotated[
    str, mapped_column(String(64), ForeignKey("matches.match_id", ondelete="CASCADE"))
]

# Simple, safe Annotated types for basic field patterns
AutoIncrementPK = Annotated[int, mapped_column(Integer, primary_key=True)]
RequiredString = Annotated[str, mapped_column(nullable=False)]
OptionalString = Annotated[Optional[str], mapped_column()]
RequiredInt = Annotated[int, mapped_column(nullable=False)]
OptionalInt = Annotated[Optional[int], mapped_column()]
RequiredBool = Annotated[bool, mapped_column(nullable=False)]
OptionalBool = Annotated[Optional[bool], mapped_column()]
RequiredDecimal = Annotated[Decimal, mapped_column(nullable=False)]
OptionalDecimal = Annotated[Optional[Decimal], mapped_column()]
RequiredBigInt = Annotated[int, mapped_column(BigInteger, nullable=False)]
OptionalBigInt = Annotated[Optional[int], mapped_column(BigInteger)]
RequiredDateTime = Annotated[datetime, mapped_column(nullable=False)]
OptionalDateTime = Annotated[Optional[datetime], mapped_column()]

# Auto-incrementing primary keys are defined above as AutoIncrementPK

# Basic field patterns that work reliably
PUUIDField = Annotated[str, mapped_column(String(78), primary_key=True, index=True)]
PUUIDForeignKey = Annotated[
    str, mapped_column(String(78), ForeignKey("players.puuid", ondelete="CASCADE"))
]
MatchIDField = Annotated[str, mapped_column(String(64), primary_key=True, index=True)]
MatchIDForeignKey = Annotated[
    str, mapped_column(String(64), ForeignKey("matches.match_id", ondelete="CASCADE"))
]

# Import all models here to ensure they are registered with SQLAlchemy
# fmt: off (noqa: E402)
from .players import Player  # noqa: E402
from .matches import Match  # noqa: E402
from .participants import MatchParticipant  # noqa: E402
from .ranks import PlayerRank  # noqa: E402
from .smurf_detection import SmurfDetection  # noqa: E402
from .job_tracking import JobConfiguration, JobExecution, JobStatus, JobType  # noqa: E402
from .settings import SystemSetting  # noqa: E402

# fmt: on

__all__ = [
    "Base",
    "Player",
    "Match",
    "MatchParticipant",
    "PlayerRank",
    "SmurfDetection",
    "JobConfiguration",
    "JobExecution",
    "JobStatus",
    "JobType",
    "SystemSetting",
]
