"""
Riot API client package for League of Legends API integration.

This package provides a comprehensive HTTP client for interacting with the Riot API,
including proper rate limiting, error handling, and authentication.
"""

from .client import RiotAPIClient
from .rate_limiter import RateLimiter
from .errors import (
    RiotAPIError,
    RateLimitError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    BadRequestError,
    ServiceUnavailableError,
)
from .models import (
    AccountDTO,
    SummonerDTO,
    MatchListDTO,
    MatchDTO,
    LeagueEntryDTO,
    CurrentGameInfoDTO,
)
from .endpoints import RiotAPIEndpoints

__all__ = [
    "RiotAPIClient",
    "RateLimiter",
    "RiotAPIError",
    "RateLimitError",
    "AuthenticationError",
    "ForbiddenError",
    "NotFoundError",
    "BadRequestError",
    "ServiceUnavailableError",
    "AccountDTO",
    "SummonerDTO",
    "MatchListDTO",
    "MatchDTO",
    "LeagueEntryDTO",
    "CurrentGameInfoDTO",
    "RiotAPIEndpoints",
]
