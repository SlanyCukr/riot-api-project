"""
Caching layer for Riot API responses using TTL-based in-memory cache.
"""

import time
import threading
from typing import Any, Optional, Dict, List, Tuple
import structlog

logger = structlog.get_logger(__name__)


class TTLCache:
    """Simple TTL cache with thread-safe operations."""

    def __init__(self, maxsize: int = 1000, ttl: int = 300):
        """
        Initialize TTL cache.

        Args:
            maxsize: Maximum number of entries
            ttl: Time to live in seconds
        """
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value if exists and not expired, None otherwise
        """
        with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if time.time() < expiry:
                    self._hits += 1
                    logger.debug("Cache hit", key=key, hits=self._hits)
                    return value
                else:
                    # Remove expired entry
                    del self.cache[key]
                    self._misses += 1
                    logger.debug("Cache expired", key=key)
            else:
                self._misses += 1
            return None

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self.lock:
            # Simple LRU: if cache is full, remove oldest entry
            if len(self.cache) >= self.maxsize and key not in self.cache:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                logger.debug("Cache eviction", key=oldest_key, reason="full")

            self.cache[key] = (value, time.time() + self.ttl)
            logger.debug("Cache set", key=key, ttl=self.ttl)

    def clear(self) -> None:
        """Clear all entries from cache."""
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info("Cache cleared", entries_removed=count)

    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self.lock:
            total = self._hits + self._misses
            return {
                "size": len(self.cache),
                "maxsize": self.maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
            }

    def __len__(self) -> int:
        """Get number of entries in cache."""
        return len(self.cache)


# Cache instances with appropriate TTLs based on data type
# TTL values follow Riot API best practices (docs/riot-api-reference.md lines 775-790)
account_cache = TTLCache(
    maxsize=1000, ttl=86400
)  # 24 hours - account data rarely changes
summoner_cache = TTLCache(
    maxsize=1000, ttl=86400
)  # 24 hours - summoner data rarely changes
match_cache = TTLCache(maxsize=5000, ttl=604800)  # 7 days - match data is immutable
match_list_cache = TTLCache(
    maxsize=500, ttl=300
)  # 5 minutes - match lists change frequently
league_cache = TTLCache(
    maxsize=1000, ttl=3600
)  # 1 hour - league entries change regularly
active_game_cache = TTLCache(
    maxsize=100, ttl=60
)  # 1 minute - live game state changes rapidly
featured_games_cache = TTLCache(
    maxsize=10, ttl=120
)  # 2 minutes - featured games change frequently
shard_cache = TTLCache(maxsize=100, ttl=3600)  # 1 hour - shards rarely change


class RiotAPICache:
    """
    Unified cache interface for all Riot API data types.
    """

    @staticmethod
    def get_account_by_riot_id(
        game_name: str, tag_line: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached account by Riot ID."""
        key = f"account:{game_name}:{tag_line}"
        return account_cache.get(key)

    @staticmethod
    def set_account_by_riot_id(
        game_name: str, tag_line: str, data: Dict[str, Any]
    ) -> None:
        """Cache account data by Riot ID."""
        key = f"account:{game_name}:{tag_line}"
        account_cache.set(key, data)

    @staticmethod
    def get_account_by_puuid(puuid: str) -> Optional[Dict[str, Any]]:
        """Get cached account by PUUID."""
        key = f"account_puuid:{puuid}"
        return account_cache.get(key)

    @staticmethod
    def set_account_by_puuid(puuid: str, data: Dict[str, Any]) -> None:
        """Cache account data by PUUID."""
        key = f"account_puuid:{puuid}"
        account_cache.set(key, data)

    @staticmethod
    def get_summoner_by_puuid(puuid: str) -> Optional[Dict[str, Any]]:
        """Get cached summoner by PUUID."""
        key = f"summoner_puuid:{puuid}"
        return summoner_cache.get(key)

    @staticmethod
    def set_summoner_by_puuid(puuid: str, data: Dict[str, Any]) -> None:
        """Cache summoner data by PUUID."""
        key = f"summoner_puuid:{puuid}"
        summoner_cache.set(key, data)

    @staticmethod
    def get_summoner_by_name(summoner_name: str) -> Optional[Dict[str, Any]]:
        """Get cached summoner by name."""
        key = f"summoner_name:{summoner_name.lower()}"
        return summoner_cache.get(key)

    @staticmethod
    def set_summoner_by_name(summoner_name: str, data: Dict[str, Any]) -> None:
        """Cache summoner data by name."""
        key = f"summoner_name:{summoner_name.lower()}"
        summoner_cache.set(key, data)

    @staticmethod
    def get_match(match_id: str) -> Optional[Dict[str, Any]]:
        """Get cached match by ID."""
        key = f"match:{match_id}"
        return match_cache.get(key)

    @staticmethod
    def set_match(match_id: str, data: Dict[str, Any]) -> None:
        """Cache match data by ID."""
        key = f"match:{match_id}"
        match_cache.set(key, data)

    @staticmethod
    def get_match_list(
        puuid: str,
        start: int = 0,
        count: int = 20,
        queue: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Optional[List[str]]:
        """Get cached match list by PUUID and parameters."""
        key = f"match_list:{puuid}:{start}:{count}:{queue}:{start_time}:{end_time}"
        return match_list_cache.get(key)

    @staticmethod
    def set_match_list(
        puuid: str,
        start: int,
        count: int,
        data: List[str],
        queue: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> None:
        """Cache match list data."""
        key = f"match_list:{puuid}:{start}:{count}:{queue}:{start_time}:{end_time}"
        match_list_cache.set(key, data)

    @staticmethod
    def get_league_entries(summoner_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached league entries."""
        key = f"league:{summoner_id}"
        return league_cache.get(key)

    @staticmethod
    def set_league_entries(summoner_id: str, data: List[Dict[str, Any]]) -> None:
        """Cache league entries data."""
        key = f"league:{summoner_id}"
        league_cache.set(key, data)

    @staticmethod
    def get_active_game(summoner_id: str) -> Optional[Dict[str, Any]]:
        """Get cached active game."""
        key = f"active_game:{summoner_id}"
        return active_game_cache.get(key)

    @staticmethod
    def set_active_game(summoner_id: str, data: Dict[str, Any]) -> None:
        """Cache active game data."""
        key = f"active_game:{summoner_id}"
        active_game_cache.set(key, data)

    @staticmethod
    def get_featured_games() -> Optional[Dict[str, Any]]:
        """Get cached featured games."""
        return featured_games_cache.get("featured_games")

    @staticmethod
    def set_featured_games(data: Dict[str, Any]) -> None:
        """Cache featured games data."""
        featured_games_cache.set("featured_games", data)

    @staticmethod
    def get_active_shard(
        puuid: str, game: str = "lol"
    ) -> Optional[Dict[str, Any]]:
        """Get cached active shard."""
        key = f"shard:{game}:{puuid}"
        return shard_cache.get(key)

    @staticmethod
    def set_active_shard(
        puuid: str, data: Dict[str, Any], game: str = "lol"
    ) -> None:
        """Cache active shard data."""
        key = f"shard:{game}:{puuid}"
        shard_cache.set(key, data)

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Get statistics from all caches."""
        return {
            "account_cache": account_cache.stats(),
            "summoner_cache": summoner_cache.stats(),
            "match_cache": match_cache.stats(),
            "match_list_cache": match_list_cache.stats(),
            "league_cache": league_cache.stats(),
            "active_game_cache": active_game_cache.stats(),
            "featured_games_cache": featured_games_cache.stats(),
            "shard_cache": shard_cache.stats(),
        }

    @staticmethod
    def clear_all() -> None:
        """Clear all caches."""
        account_cache.clear()
        summoner_cache.clear()
        match_cache.clear()
        match_list_cache.clear()
        league_cache.clear()
        active_game_cache.clear()
        featured_games_cache.clear()
        shard_cache.clear()
        logger.info("All caches cleared")


# For backward compatibility, create module-level functions
get_cached_account_by_riot_id = RiotAPICache.get_account_by_riot_id
set_cached_account_by_riot_id = RiotAPICache.set_account_by_riot_id
get_cached_account_by_puuid = RiotAPICache.get_account_by_puuid
set_cached_account_by_puuid = RiotAPICache.set_account_by_puuid
get_cached_summoner_by_puuid = RiotAPICache.get_summoner_by_puuid
set_cached_summoner_by_puuid = RiotAPICache.set_summoner_by_puuid
get_cached_summoner_by_name = RiotAPICache.get_summoner_by_name
set_cached_summoner_by_name = RiotAPICache.set_summoner_by_name
get_cached_match = RiotAPICache.get_match
set_cached_match = RiotAPICache.set_match
get_cached_match_list = RiotAPICache.get_match_list
set_cached_match_list = RiotAPICache.set_match_list
get_cached_league_entries = RiotAPICache.get_league_entries
set_cached_league_entries = RiotAPICache.set_league_entries
get_cached_active_game = RiotAPICache.get_active_game
set_cached_active_game = RiotAPICache.set_active_game
get_cached_featured_games = RiotAPICache.get_featured_games
set_cached_featured_games = RiotAPICache.set_featured_games
