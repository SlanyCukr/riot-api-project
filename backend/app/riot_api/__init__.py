"""
Riot API client package for League of Legends API integration.

This package provides a comprehensive HTTP client for interacting with the Riot API,
including proper rate limiting, error handling, authentication, and caching.
"""

from .client import RiotAPIClient
from .rate_limiter import RateLimiter
from .errors import RiotAPIError, RateLimitError, AuthenticationError
from .models import (
    AccountDTO,
    SummonerDTO,
    MatchListDTO,
    MatchDTO,
    LeagueEntryDTO,
    CurrentGameInfoDTO
)
from .cache import RiotAPICache
from .endpoints import RiotAPIEndpoints

__all__ = [
    "RiotAPIClient",
    "RateLimiter",
    "RiotAPIError",
    "RateLimitError",
    "AuthenticationError",
    "AccountDTO",
    "SummonerDTO",
    "MatchListDTO",
    "MatchDTO",
    "LeagueEntryDTO",
    "CurrentGameInfoDTO",
    "RiotAPICache",
    "RiotAPIEndpoints"
]