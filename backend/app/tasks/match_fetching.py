"""
Match fetching background tasks for async data retrieval from Riot API.

Provides tasks for fetching match data, updating player histories,
and managing data freshness with rate limiting.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import structlog

from ..riot_api.client import RiotAPIClient
from ..database import get_db
from ..models.players import Player
from ..services.matches import MatchService
from ..tasks.queue import BackgroundTask

logger = structlog.get_logger(__name__)


class MatchFetchingTasks:
    """Background tasks for fetching and updating match data."""

    def __init__(self, db: AsyncSession, riot_client: RiotAPIClient):
        """
        Initialize match fetching tasks.

        Args:
            db: Database session
            riot_client: Riot API client
        """
        self.db = db
        self.riot_client = riot_client
        self.match_service = MatchService(db, riot_client)

    async def fetch_player_matches(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch recent matches for a player.

        Args:
            task_data: Task data containing puuid and fetch parameters

        Returns:
            Dictionary with fetch results
        """
        puuid = task_data['puuid']
        limit = task_data.get('limit', 50)
        queue_filter = task_data.get('queue_filter')  # 420 for ranked solo
        start_time = task_data.get('start_time')
        end_time = task_data.get('end_time')

        logger.info("Fetching player matches", puuid=puuid, limit=limit)

        try:
            # Get match list from API
            match_ids = await self.riot_client.get_match_list_by_puuid(
                puuid=puuid,
                start=0,
                count=limit,
                queue=queue_filter,
                start_time=start_time,
                end_time=end_time
            )

            # Fetch match details for each match
            fetched_matches = 0
            errors = []

            for i, match_id in enumerate(match_ids):
                try:
                    match_data = await self.riot_client.get_match(match_id)
                    await self.match_service._store_match_detail(match_data)
                    fetched_matches += 1

                    # Rate limiting - small delay between requests
                    if i < len(match_ids) - 1:
                        await asyncio.sleep(0.1)

                except Exception as e:
                    error_msg = f"Failed to fetch match {match_id}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning("Failed to fetch match details", match_id=match_id, error=str(e))

            # Update player last seen timestamp
            await self._update_player_last_seen(puuid)

            logger.info(
                "Player matches fetched",
                puuid=puuid,
                total_matches=len(match_ids),
                successfully_fetched=fetched_matches,
                errors=len(errors)
            )

            return {
                'puuid': puuid,
                'total_matches': len(match_ids),
                'fetched_matches': fetched_matches,
                'errors': errors,
                'queue_filter': queue_filter,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to fetch player matches", puuid=puuid, error=str(e))
            raise

    async def update_active_players(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update match data for recently active players.

        Args:
            task_data: Task data containing update parameters

        Returns:
            Dictionary with update results
        """
        limit = task_data.get('limit', 20)  # Update 20 most active players
        days_threshold = task_data.get('days_threshold', 7)  # Active in last 7 days
        matches_per_player = task_data.get('matches_per_player', 20)

        logger.info("Updating active players", limit=limit, days_threshold=days_threshold)

        try:
            # Get players active in the last N days
            cutoff_date = datetime.now() - timedelta(days=days_threshold)

            query = select(Player.puuid).where(
                and_(
                    Player.last_seen >= cutoff_date,
                    Player.puuid.isnot(None)
                )
            ).order_by(Player.last_seen.desc()).limit(limit)

            result = await self.db.execute(query)
            active_players = result.scalars().all()

            updated_players = 0
            errors = []

            for i, puuid in enumerate(active_players):
                try:
                    # Queue match fetching task for this player
                    fetch_result = await self.fetch_player_matches({
                        'puuid': puuid,
                        'limit': matches_per_player,
                        'queue_filter': 420  # Ranked matches only
                    })

                    if fetch_result['fetched_matches'] > 0:
                        updated_players += 1

                    # Small delay between players to respect rate limits
                    if i < len(active_players) - 1:
                        await asyncio.sleep(0.5)

                except Exception as e:
                    error_msg = f"Failed to update player {puuid}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning("Failed to update player", puuid=puuid, error=str(e))

            logger.info(
                "Active players updated",
                total_players=len(active_players),
                successfully_updated=updated_players,
                errors=len(errors)
            )

            return {
                'total_players': len(active_players),
                'updated_players': updated_players,
                'errors': errors,
                'days_threshold': days_threshold,
                'matches_per_player': matches_per_player,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to update active players", error=str(e))
            raise

    async def fetch_missing_matches(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch missing match data for players with incomplete histories.

        Args:
            task_data: Task data containing fetch parameters

        Returns:
            Dictionary with fetch results
        """
        player_puuids = task_data.get('puuids', [])
        min_matches = task_data.get('min_matches', 50)
        days_back = task_data.get('days_back', 30)

        logger.info("Fetching missing matches", players=len(player_puuids))

        try:
            if not player_puuids:
                # Get players with insufficient match data
                cutoff_date = datetime.now() - timedelta(days=days_back)
                query = select(Player.puuid).where(
                    and_(
                        Player.last_seen >= cutoff_date,
                        Player.puuid.isnot(None)
                    )
                )

                result = await self.db.execute(query)
                player_puuids = result.scalars().all()

            fetched_matches = 0
            updated_players = 0
            errors = []

            for i, puuid in enumerate(player_puuids):
                try:
                    # Check current match count for player
                    from ..models.matches import Match
                    from ..models.participants import MatchParticipant

                    match_count_query = select(func.count(Match.match_id)).join(
                        MatchParticipant, Match.match_id == MatchParticipant.match_id
                    ).where(MatchParticipant.puuid == puuid)

                    result = await self.db.execute(match_count_query)
                    current_matches = result.scalar() or 0

                    if current_matches < min_matches:
                        fetch_result = await self.fetch_player_matches({
                            'puuid': puuid,
                            'limit': min_matches - current_matches,
                            'queue_filter': 420
                        })

                        if fetch_result['fetched_matches'] > 0:
                            updated_players += 1
                            fetched_matches += fetch_result['fetched_matches']

                    # Delay between players
                    if i < len(player_puuids) - 1:
                        await asyncio.sleep(0.3)

                except Exception as e:
                    error_msg = f"Failed to fetch matches for player {puuid}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning("Failed to fetch missing matches", puuid=puuid, error=str(e))

            logger.info(
                "Missing matches fetched",
                players_processed=len(player_puuids),
                updated_players=updated_players,
                total_matches_fetched=fetched_matches,
                errors=len(errors)
            )

            return {
                'players_processed': len(player_puuids),
                'updated_players': updated_players,
                'total_matches_fetched': fetched_matches,
                'errors': errors,
                'min_matches': min_matches,
                'days_back': days_back,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to fetch missing matches", error=str(e))
            raise

    async def refresh_stale_player_data(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Refresh data for players with stale information.

        Args:
            task_data: Task data containing refresh parameters

        Returns:
            Dictionary with refresh results
        """
        days_stale = task_data.get('days_stale', 14)  # Consider data stale after 14 days
        limit = task_data.get('limit', 50)

        logger.info("Refreshing stale player data", days_stale=days_stale, limit=limit)

        try:
            # Get players with stale data
            cutoff_date = datetime.now() - timedelta(days=days_stale)

            query = select(Player.puuid).where(
                and_(
                    Player.last_seen < cutoff_date,
                    Player.puuid.isnot(None)
                )
            ).order_by(Player.last_seen.asc()).limit(limit)

            result = await self.db.execute(query)
            stale_players = result.scalars().all()

            refreshed_players = 0
            errors = []

            for i, puuid in enumerate(stale_players):
                try:
                    # Fetch recent matches for stale player
                    fetch_result = await self.fetch_player_matches({
                        'puuid': puuid,
                        'limit': 10,  # Just get recent matches to refresh
                        'queue_filter': None  # All queues
                    })

                    if fetch_result['fetched_matches'] > 0:
                        refreshed_players += 1

                    # Delay between players
                    if i < len(stale_players) - 1:
                        await asyncio.sleep(0.3)

                except Exception as e:
                    error_msg = f"Failed to refresh player {puuid}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning("Failed to refresh player", puuid=puuid, error=str(e))

            logger.info(
                "Stale player data refreshed",
                total_players=len(stale_players),
                refreshed_players=refreshed_players,
                errors=len(errors)
            )

            return {
                'total_players': len(stale_players),
                'refreshed_players': refreshed_players,
                'errors': errors,
                'days_stale': days_stale,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to refresh stale player data", error=str(e))
            raise

    async def batch_fetch_matches(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Batch fetch matches for multiple players.

        Args:
            task_data: Task data containing batch parameters

        Returns:
            Dictionary with batch fetch results
        """
        player_puuids = task_data['puuids']
        matches_per_player = task_data.get('matches_per_player', 20)
        batch_size = task_data.get('batch_size', 10)
        delay_between_players = task_data.get('delay_seconds', 2)
        queue_filter = task_data.get('queue_filter')

        logger.info("Starting batch match fetch", total_players=len(player_puuids))

        try:
            total_fetched = 0
            successful_players = 0
            errors = []

            for i, puuid in enumerate(player_puuids):
                try:
                    result = await self.fetch_player_matches({
                        'puuid': puuid,
                        'limit': matches_per_player,
                        'queue_filter': queue_filter
                    })

                    if result['fetched_matches'] > 0:
                        successful_players += 1
                        total_fetched += result['fetched_matches']

                    # Log progress
                    if (i + 1) % batch_size == 0:
                        logger.info(
                            "Batch fetch progress",
                            processed=i + 1,
                            successful_players=successful_players,
                            total_matches_fetched=total_fetched,
                            remaining=len(player_puuids) - (i + 1)
                        )

                except Exception as e:
                    error_msg = f"Failed to fetch matches for player {puuid}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning("Failed to fetch matches in batch", puuid=puuid, error=str(e))

                # Delay between players to respect rate limits
                if i < len(player_puuids) - 1:
                    await asyncio.sleep(delay_between_players)

            logger.info(
                "Batch fetch completed",
                total_players=len(player_puuids),
                successful_players=successful_players,
                total_matches_fetched=total_fetched,
                errors=len(errors)
            )

            return {
                'total_players': len(player_puuids),
                'successful_players': successful_players,
                'total_matches_fetched': total_fetched,
                'errors': errors,
                'matches_per_player': matches_per_player,
                'queue_filter': queue_filter,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to batch fetch matches", error=str(e))
            raise

    async def _update_player_last_seen(self, puuid: str):
        """Update player's last seen timestamp."""
        try:
            result = await self.db.execute(
                select(Player).where(Player.puuid == puuid)
            )
            player = result.scalar_one_or_none()

            if player:
                player.last_seen = datetime.now()
                await self.db.commit()
        except Exception as e:
            logger.error("Failed to update player last seen", puuid=puuid, error=str(e))
            await self.db.rollback()