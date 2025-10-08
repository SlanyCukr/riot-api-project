"""
Tests for cache implementation.
"""

import pytest
import time

from app.riot_api.cache import RiotAPICache, TTLCache, clear_all_caches


class TestTTLCache:
    """Test cases for TTLCache."""

    def test_initialization(self):
        """Test TTL cache initialization."""
        cache = TTLCache(maxsize=100, ttl=60)
        assert cache.maxsize == 100
        assert cache.ttl == 60
        assert len(cache.cache) == 0

    def test_set_and_get(self):
        """Test setting and getting cache entries."""
        cache = TTLCache(maxsize=10, ttl=60)

        # Set entry
        cache.set("test_key", "test_value")
        assert len(cache.cache) == 1

        # Get entry
        value = cache.get("test_key")
        assert value == "test_value"

    def test_get_nonexistent_key(self):
        """Test getting nonexistent key."""
        cache = TTLCache(maxsize=10, ttl=60)
        value = cache.get("nonexistent_key")
        assert value is None

    def test_ttl_expiration(self):
        """Test TTL expiration."""
        cache = TTLCache(maxsize=10, ttl=1)  # 1 second TTL

        # Set entry
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"

        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("test_key") is None

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = TTLCache(maxsize=2, ttl=60)

        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert len(cache.cache) == 2

        # Add one more entry - should evict oldest
        cache.set("key3", "value3")
        assert len(cache.cache) == 2
        assert cache.get("key1") is None  # key1 should be evicted
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_clear(self):
        """Test clearing cache."""
        cache = TTLCache(maxsize=10, ttl=60)

        # Add entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert len(cache.cache) == 2

        # Clear cache
        cache.clear()
        assert len(cache.cache) == 0

    def test_len(self):
        """Test cache length."""
        cache = TTLCache(maxsize=10, ttl=60)
        assert len(cache) == 0

        cache.set("key1", "value1")
        assert len(cache) == 1

        cache.set("key2", "value2")
        assert len(cache) == 2


class TestRiotAPICache:
    """Test cases for RiotAPICache."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test Riot API cache initialization."""
        cache = RiotAPICache(max_size=100)
        assert cache is not None

    @pytest.mark.asyncio
    async def test_account_by_riot_id(self):
        """Test account caching by Riot ID."""
        cache = RiotAPICache()
        test_data = {"puuid": "test-puuid", "game_name": "test", "tag_line": "1234"}

        # Set cache
        await cache.set_account_by_riot_id("test", "1234", test_data)

        # Get from cache
        cached_data = await cache.get_account_by_riot_id("test", "1234")
        assert cached_data == test_data

        # Test nonexistent key
        nonexistent = await cache.get_account_by_riot_id("nonexistent", "5678")
        assert nonexistent is None

    @pytest.mark.asyncio
    async def test_account_by_puuid(self):
        """Test account caching by PUUID."""
        cache = RiotAPICache()
        test_data = {"puuid": "test-puuid", "game_name": "test", "tag_line": "1234"}

        # Set cache
        await cache.set_account_by_puuid("test-puuid", test_data)

        # Get from cache
        cached_data = await cache.get_account_by_puuid("test-puuid")
        assert cached_data == test_data

    @pytest.mark.asyncio
    async def test_summoner_by_name(self):
        """Test summoner caching by name."""
        cache = RiotAPICache()
        test_data = {"name": "TestSummoner", "puuid": "test-puuid", "level": 30}

        # Set cache
        await cache.set_summoner_by_name("TestSummoner", test_data)

        # Get from cache (case insensitive)
        cached_data = await cache.get_summoner_by_name("testsummoner")
        assert cached_data == test_data

    @pytest.mark.asyncio
    async def test_match_data(self):
        """Test match data caching."""
        cache = RiotAPICache()
        test_data = {"match_id": "test-match", "game_duration": 1800}

        # Set cache
        await cache.set_match("test-match", test_data)

        # Get from cache
        cached_data = await cache.get_match("test-match")
        assert cached_data == test_data

    @pytest.mark.asyncio
    async def test_match_list(self):
        """Test match list caching."""
        cache = RiotAPICache()
        test_data = {"matches": [{"match_id": "match1"}, {"match_id": "match2"}]}

        # Set cache
        await cache.set_match_list_by_puuid("test-puuid", 0, 20, test_data)

        # Get from cache
        cached_data = await cache.get_match_list_by_puuid("test-puuid", 0, 20)
        assert cached_data == test_data

        # Test with different parameters
        different_params = await cache.get_match_list_by_puuid("test-puuid", 20, 20)
        assert different_params is None

    @pytest.mark.asyncio
    async def test_league_entries(self):
        """Test league entries caching."""
        cache = RiotAPICache()
        test_data = [{"tier": "Gold", "rank": "I"}]

        # Set cache
        await cache.set_league_entries("summoner123", test_data)

        # Get from cache
        cached_data = await cache.get_league_entries("summoner123")
        assert cached_data == test_data

    @pytest.mark.asyncio
    async def test_active_game(self):
        """Test active game caching."""
        cache = RiotAPICache()
        test_data = {"game_id": "game123", "game_mode": "CLASSIC"}

        # Set cache
        await cache.set_active_game("summoner123", test_data)

        # Get from cache
        cached_data = await cache.get_active_game("summoner123")
        assert cached_data == test_data

    @pytest.mark.asyncio
    async def test_featured_games(self):
        """Test featured games caching."""
        cache = RiotAPICache()
        test_data = {"gameList": [{"gameId": "game1"}, {"gameId": "game2"}]}

        # Set cache
        await cache.set_featured_games(test_data)

        # Get from cache
        cached_data = await cache.get_featured_games()
        assert cached_data == test_data

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test clearing all cache."""
        cache = RiotAPICache()
        test_data = {"test": "data"}

        # Set some data
        await cache.set_account_by_puuid("test-puuid", test_data)
        await cache.set_match("test-match", test_data)
        await cache.set_summoner_by_name("test", test_data)

        # Verify data is cached
        assert await cache.get_account_by_puuid("test-puuid") is not None
        assert await cache.get_match("test-match") is not None
        assert await cache.get_summoner_by_name("test") is not None

        # Clear cache
        await cache.clear()

        # Verify cache is empty
        assert await cache.get_account_by_puuid("test-puuid") is None
        assert await cache.get_match("test-match") is None
        assert await cache.get_summoner_by_name("test") is None

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting cache statistics."""
        cache = RiotAPICache()

        # Initially empty
        stats = await cache.get_stats()
        assert "account_cache" in stats
        assert "match_cache" in stats
        assert "summoner_cache" in stats

        # Add some data
        test_data = {"test": "data"}
        await cache.set_account_by_puuid("test-puuid", test_data)
        await cache.set_match("test-match", test_data)

        # Check stats again
        stats = await cache.get_stats()
        # Note: stats might still show 0 entries due to TTL cache behavior
        assert "account_cache" in stats
        assert "match_cache" in stats

    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        """Test cleanup of expired entries (should be no-op with TTLCache)."""
        cache = RiotAPICache()

        # This should not raise an exception
        await cache.cleanup_expired()

        # Verify cache still works
        test_data = {"test": "data"}
        await cache.set_account_by_puuid("test-puuid", test_data)
        assert await cache.get_account_by_puuid("test-puuid") == test_data


class TestCacheUtilityFunctions:
    """Test cases for cache utility functions."""

    def test_clear_all_caches(self):
        """Test clearing all caches utility function."""
        # This function should not raise an exception
        clear_all_caches()

        # Verify we can still use caches after clearing
        cache = RiotAPICache()
        # No exception should be raised
        assert cache is not None
