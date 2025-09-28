"""
Caching layer for Riot API responses using functools.lru_cache.
"""

import time
import threading
from typing import Any, Optional, Dict, List
from functools import lru_cache
import structlog

logger = structlog.get_logger(__name__)

# Simple time-based cache with TTL support
class TTLCache:
    """Simple TTL cache wrapper around lru_cache."""

    def __init__(self, maxsize: int = 1000, ttl: int = 300):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache = {}
        self.lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if time.time() < expiry:
                    return value
                else:
                    # Remove expired entry
                    del self.cache[key]
            return None

    def set(self, key: str, value: Any) -> None:
        """Set value in cache with TTL."""
        with self.lock:
            # Simple LRU: if cache is full, remove oldest entry
            if len(self.cache) >= self.maxsize:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]

            self.cache[key] = (value, time.time() + self.ttl)

    def clear(self) -> None:
        """Clear all entries from cache."""
        with self.lock:
            self.cache.clear()

    def __len__(self) -> int:
        """Get number of entries in cache."""
        return len(self.cache)

# Cache instances with appropriate TTLs based on data type
account_cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hour - account data rarely changes
summoner_cache = TTLCache(maxsize=1000, ttl=1800)  # 30 minutes - summoner data changes occasionally
match_cache = TTLCache(maxsize=5000, ttl=86400)  # 24 hours - match data is immutable
match_list_cache = TTLCache(maxsize=500, ttl=300)  # 5 minutes - match lists change frequently
league_cache = TTLCache(maxsize=1000, ttl=600)  # 10 minutes - league entries change frequently
active_game_cache = TTLCache(maxsize=100, ttl=60)  # 1 minute - active games change very frequently
featured_games_cache = TTLCache(maxsize=10, ttl=120)  # 2 minutes - featured games change frequently
shard_cache = TTLCache(maxsize=100, ttl=3600)  # 1 hour - shards rarely change

# Account data caching functions
@lru_cache(maxsize=1000)
def cache_account_by_riot_id(game_name: str, tag_line: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Cache account data by Riot ID."""
    logger.debug("Cached account by Riot ID", game_name=game_name, tag_line=tag_line)
    return data

def get_cached_account_by_riot_id(game_name: str, tag_line: str) -> Optional[Dict[str, Any]]:
    """Get cached account by Riot ID."""
    return account_cache.get(f"account:{game_name}:{tag_line}")

def set_cached_account_by_riot_id(game_name: str, tag_line: str, data: Dict[str, Any]) -> None:
    """Set cached account by Riot ID."""
    account_cache.set(f"account:{game_name}:{tag_line}", data)

@lru_cache(maxsize=1000)
def cache_account_by_puuid(puuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Cache account data by PUUID."""
    logger.debug("Cached account by PUUID", puuid=puuid)
    return data

def get_cached_account_by_puuid(puuid: str) -> Optional[Dict[str, Any]]:
    """Get cached account by PUUID."""
    return account_cache.get(f"account_puuid:{puuid}")

def set_cached_account_by_puuid(puuid: str, data: Dict[str, Any]) -> None:
    """Set cached account by PUUID."""
    account_cache.set(f"account_puuid:{puuid}", data)

# Summoner data caching functions
@lru_cache(maxsize=1000)
def cache_summoner_by_puuid(puuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Cache summoner data by PUUID."""
    logger.debug("Cached summoner by PUUID", puuid=puuid)
    return data

def get_cached_summoner_by_puuid(puuid: str) -> Optional[Dict[str, Any]]:
    """Get cached summoner by PUUID."""
    return summoner_cache.get(f"summoner_puuid:{puuid}")

def set_cached_summoner_by_puuid(puuid: str, data: Dict[str, Any]) -> None:
    """Set cached summoner by PUUID."""
    summoner_cache.set(f"summoner_puuid:{puuid}", data)

@lru_cache(maxsize=1000)
def cache_summoner_by_name(summoner_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Cache summoner data by name."""
    logger.debug("Cached summoner by name", summoner_name=summoner_name)
    return data

def get_cached_summoner_by_name(summoner_name: str) -> Optional[Dict[str, Any]]:
    """Get cached summoner by name."""
    return summoner_cache.get(f"summoner_name:{summoner_name.lower()}")

def set_cached_summoner_by_name(summoner_name: str, data: Dict[str, Any]) -> None:
    """Set cached summoner by name."""
    summoner_cache.set(f"summoner_name:{summoner_name.lower()}", data)

# Match data caching functions
@lru_cache(maxsize=5000)
def cache_match(match_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Cache match data by ID."""
    logger.debug("Cached match", match_id=match_id)
    return data

def get_cached_match(match_id: str) -> Optional[Dict[str, Any]]:
    """Get cached match by ID."""
    return match_cache.get(f"match:{match_id}")

def set_cached_match(match_id: str, data: Dict[str, Any]) -> None:
    """Set cached match by ID."""
    match_cache.set(f"match:{match_id}", data)

# Match list caching functions
def get_match_list_cache_key(puuid: str, start: int, count: int, queue: Optional[int] = None, start_time: Optional[int] = None, end_time: Optional[int] = None) -> str:
    """Generate cache key for match list."""
    return f"match_list:{puuid}:{start}:{count}:{queue}:{start_time}:{end_time}"

@lru_cache(maxsize=500)
def cache_match_list(puuid: str, start: int, count: int, data: Dict[str, Any], queue: Optional[int] = None, start_time: Optional[int] = None, end_time: Optional[int] = None) -> Dict[str, Any]:
    """Cache match list by PUUID."""
    logger.debug("Cached match list", puuid=puuid, start=start, count=count)
    return data

def get_cached_match_list(puuid: str, start: int = 0, count: int = 20, queue: Optional[int] = None, start_time: Optional[int] = None, end_time: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Get cached match list by PUUID."""
    key = get_match_list_cache_key(puuid, start, count, queue, start_time, end_time)
    return match_list_cache.get(key)

def set_cached_match_list(puuid: str, start: int, count: int, data: Dict[str, Any], queue: Optional[int] = None, start_time: Optional[int] = None, end_time: Optional[int] = None) -> None:
    """Set cached match list by PUUID."""
    key = get_match_list_cache_key(puuid, start, count, queue, start_time, end_time)
    match_list_cache.set(key, data)

# League data caching functions
@lru_cache(maxsize=1000)
def cache_league_entries(summoner_id: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Cache league entries by summoner ID."""
    logger.debug("Cached league entries", summoner_id=summoner_id)
    return data

def get_cached_league_entries(summoner_id: str) -> Optional[List[Dict[str, Any]]]:
    """Get cached league entries."""
    return league_cache.get(f"league:{summoner_id}")

def set_cached_league_entries(summoner_id: str, data: List[Dict[str, Any]]) -> None:
    """Set cached league entries."""
    league_cache.set(f"league:{summoner_id}", data)

# Active game caching functions
@lru_cache(maxsize=100)
def cache_active_game(summoner_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Cache active game by summoner ID."""
    logger.debug("Cached active game", summoner_id=summoner_id)
    return data

def get_cached_active_game(summoner_id: str) -> Optional[Dict[str, Any]]:
    """Get cached active game."""
    return active_game_cache.get(f"active_game:{summoner_id}")

def set_cached_active_game(summoner_id: str, data: Dict[str, Any]) -> None:
    """Set cached active game."""
    active_game_cache.set(f"active_game:{summoner_id}", data)

# Featured games caching functions
@lru_cache(maxsize=10)
def cache_featured_games(data: Dict[str, Any]) -> Dict[str, Any]:
    """Cache featured games."""
    logger.debug("Cached featured games")
    return data

def get_cached_featured_games() -> Optional[Dict[str, Any]]:
    """Get cached featured games."""
    return featured_games_cache.get("featured_games")

def set_cached_featured_games(data: Dict[str, Any]) -> None:
    """Set cached featured games."""
    featured_games_cache.set("featured_games", data)

# Active shard caching functions
@lru_cache(maxsize=100)
def cache_active_shard(puuid: str, game: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Cache active shard data."""
    logger.debug("Cached active shard", puuid=puuid, game=game)
    return data

def get_cached_active_shard(puuid: str, game: str) -> Optional[Dict[str, Any]]:
    """Get cached active shard."""
    return shard_cache.get(f"shard:{puuid}:{game}")

def set_cached_active_shard(puuid: str, game: str, data: Dict[str, Any]) -> None:
    """Set cached active shard."""
    shard_cache.set(f"shard:{puuid}:{game}", data)

class RiotAPICache:
    """
    Simplified Riot API cache interface using functools.lru_cache.
    Maintains backward compatibility with the existing API.
    """

    def __init__(self, max_size: int = 1000):
        """Initialize Riot API cache."""
        # max_size parameter kept for backward compatibility
        logger.debug("Initialized simplified Riot API cache")

    async def get_account_by_riot_id(self, game_name: str, tag_line: str) -> Optional[Dict[str, Any]]:
        """Get cached account by Riot ID."""
        return get_cached_account_by_riot_id(game_name, tag_line)

    async def set_account_by_riot_id(self, game_name: str, tag_line: str, data: Dict[str, Any]) -> None:
        """Set cached account by Riot ID."""
        set_cached_account_by_riot_id(game_name, tag_line, data)

    async def get_account_by_puuid(self, puuid: str) -> Optional[Dict[str, Any]]:
        """Get cached account by PUUID."""
        return get_cached_account_by_puuid(puuid)

    async def set_account_by_puuid(self, puuid: str, data: Dict[str, Any]) -> None:
        """Set cached account by PUUID."""
        set_cached_account_by_puuid(puuid, data)

    async def get_summoner_by_puuid(self, puuid: str) -> Optional[Dict[str, Any]]:
        """Get cached summoner by PUUID."""
        return get_cached_summoner_by_puuid(puuid)

    async def set_summoner_by_puuid(self, puuid: str, data: Dict[str, Any]) -> None:
        """Set cached summoner by PUUID."""
        set_cached_summoner_by_puuid(puuid, data)

    async def get_summoner_by_name(self, summoner_name: str) -> Optional[Dict[str, Any]]:
        """Get cached summoner by name."""
        return get_cached_summoner_by_name(summoner_name)

    async def set_summoner_by_name(self, summoner_name: str, data: Dict[str, Any]) -> None:
        """Set cached summoner by name."""
        set_cached_summoner_by_name(summoner_name, data)

    async def get_match_list_by_puuid(
        self,
        puuid: str,
        start: int = 0,
        count: int = 20,
        queue: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached match list by PUUID."""
        return get_cached_match_list(puuid, start, count, queue, start_time, end_time)

    async def set_match_list_by_puuid(
        self,
        puuid: str,
        start: int,
        count: int,
        data: Dict[str, Any],
        queue: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> None:
        """Set cached match list by PUUID."""
        set_cached_match_list(puuid, start, count, data, queue, start_time, end_time)

    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get cached match by ID."""
        return get_cached_match(match_id)

    async def set_match(self, match_id: str, data: Dict[str, Any]) -> None:
        """Set cached match by ID."""
        set_cached_match(match_id, data)

    async def get_league_entries(self, summoner_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached league entries."""
        return get_cached_league_entries(summoner_id)

    async def set_league_entries(self, summoner_id: str, data: List[Dict[str, Any]]) -> None:
        """Set cached league entries."""
        set_cached_league_entries(summoner_id, data)

    async def get_active_game(self, summoner_id: str) -> Optional[Dict[str, Any]]:
        """Get cached active game."""
        return get_cached_active_game(summoner_id)

    async def set_active_game(self, summoner_id: str, data: Dict[str, Any]) -> None:
        """Set cached active game."""
        set_cached_active_game(summoner_id, data)

    async def get_featured_games(self) -> Optional[Dict[str, Any]]:
        """Get cached featured games."""
        return get_cached_featured_games()

    async def set_featured_games(self, data: Dict[str, Any]) -> None:
        """Set cached featured games."""
        set_cached_featured_games(data)

    async def get_active_shard(self, puuid: str, game: str) -> Optional[Dict[str, Any]]:
        """Get cached active shard."""
        return get_cached_active_shard(puuid, game)

    async def set_active_shard(self, puuid: str, game: str, data: Dict[str, Any]) -> None:
        """Set cached active shard."""
        set_cached_active_shard(puuid, game, data)

    async def clear(self) -> None:
        """Clear all cached data."""
        for cache in [account_cache, summoner_cache, match_cache, match_list_cache,
                      league_cache, active_game_cache, featured_games_cache, shard_cache]:
            cache.clear()
        # Clear lru_cache decorators
        cache_account_by_riot_id.cache_clear()
        cache_account_by_puuid.cache_clear()
        cache_summoner_by_puuid.cache_clear()
        cache_summoner_by_name.cache_clear()
        cache_match.cache_clear()
        cache_match_list.cache_clear()
        cache_league_entries.cache_clear()
        cache_active_game.cache_clear()
        cache_featured_games.cache_clear()
        cache_active_shard.cache_clear()
        logger.debug("Cleared all Riot API caches")

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "account_cache": {
                "total_entries": len(account_cache),
                "max_size": account_cache.maxsize,
                "ttl": account_cache.ttl,
                "lru_cache_info": cache_account_by_riot_id.cache_info()
            },
            "summoner_cache": {
                "total_entries": len(summoner_cache),
                "max_size": summoner_cache.maxsize,
                "ttl": summoner_cache.ttl,
                "lru_cache_info": cache_summoner_by_puuid.cache_info()
            },
            "match_cache": {
                "total_entries": len(match_cache),
                "max_size": match_cache.maxsize,
                "ttl": match_cache.ttl,
                "lru_cache_info": cache_match.cache_info()
            },
            "match_list_cache": {
                "total_entries": len(match_list_cache),
                "max_size": match_list_cache.maxsize,
                "ttl": match_list_cache.ttl,
                "lru_cache_info": cache_match_list.cache_info()
            },
            "league_cache": {
                "total_entries": len(league_cache),
                "max_size": league_cache.maxsize,
                "ttl": league_cache.ttl,
                "lru_cache_info": cache_league_entries.cache_info()
            },
            "active_game_cache": {
                "total_entries": len(active_game_cache),
                "max_size": active_game_cache.maxsize,
                "ttl": active_game_cache.ttl,
                "lru_cache_info": cache_active_game.cache_info()
            },
            "featured_games_cache": {
                "total_entries": len(featured_games_cache),
                "max_size": featured_games_cache.maxsize,
                "ttl": featured_games_cache.ttl,
                "lru_cache_info": cache_featured_games.cache_info()
            },
            "shard_cache": {
                "total_entries": len(shard_cache),
                "max_size": shard_cache.maxsize,
                "ttl": shard_cache.ttl,
                "lru_cache_info": cache_active_shard.cache_info()
            }
        }

    async def cleanup_expired(self) -> None:
        """Clean up expired entries (handled automatically by TTLCache)."""
        # TTLCache handles expiration automatically, no manual cleanup needed
        logger.debug("Cache cleanup not needed - TTLCache handles expiration automatically")


# Cache clearing functions for specific data types
def clear_account_cache():
    """Clear account cache."""
    account_cache.clear()
    cache_account_by_riot_id.cache_clear()
    cache_account_by_puuid.cache_clear()
    logger.debug("Cleared account cache")


def clear_summoner_cache():
    """Clear summoner cache."""
    summoner_cache.clear()
    cache_summoner_by_puuid.cache_clear()
    cache_summoner_by_name.cache_clear()
    logger.debug("Cleared summoner cache")


def clear_match_cache():
    """Clear match cache."""
    match_cache.clear()
    cache_match.cache_clear()
    logger.debug("Cleared match cache")


def clear_match_list_cache():
    """Clear match list cache."""
    match_list_cache.clear()
    cache_match_list.cache_clear()
    logger.debug("Cleared match list cache")


def clear_league_cache():
    """Clear league cache."""
    league_cache.clear()
    cache_league_entries.cache_clear()
    logger.debug("Cleared league cache")


def clear_active_game_cache():
    """Clear active game cache."""
    active_game_cache.clear()
    cache_active_game.cache_clear()
    logger.debug("Cleared active game cache")


def clear_all_caches():
    """Clear all caches."""
    clear_account_cache()
    clear_summoner_cache()
    clear_match_cache()
    clear_match_list_cache()
    clear_league_cache()
    clear_active_game_cache()
    featured_games_cache.clear()
    cache_featured_games.cache_clear()
    shard_cache.clear()
    cache_active_shard.cache_clear()
    logger.debug("Cleared all caches")