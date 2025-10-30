from typing import List, Dict, Any, Optional
import asyncio
import structlog

from app.core.riot_api import RiotAPIClient
from app.core.riot_api.data_manager import RiotDataManager

logger = structlog.get_logger(__name__)


class MatchmakingGateway:
    """Gateway for external API calls in matchmaking analysis"""

    def __init__(self, riot_client: RiotAPIClient, data_manager: RiotDataManager):
        self.riot_client = riot_client
        self.data_manager = data_manager

    async def fetch_match_data(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Fetch match data with retry logic and rate limiting"""
        try:
            # Use data manager which handles caching and rate limiting
            match_data = await self.data_manager.get_match(match_id)
            return match_data
        except Exception as e:
            # Log error and return None - let service layer handle
            logger.error("match_fetch_error", match_id=match_id, error=str(e))
            return None

    async def get_player_recent_matches(
        self, puuid: str, count: int = 20
    ) -> List[Dict[str, Any]]:
        """Get player's recent matches for analysis"""
        try:
            # Use riot client directly for match history (following matches/gateway pattern)
            from app.core.riot_api.constants import QueueType

            match_list = await self.riot_client.get_match_list_by_puuid(
                puuid=puuid,
                start=0,
                count=count,
                queue=QueueType.RANKED_SOLO_5X5,
            )

            # Convert to list of match dicts
            match_ids = (
                list(match_list.match_ids)
                if match_list and match_list.match_ids
                else []
            )

            # Return as list of match dicts (matchId key for consistency)
            return [{"matchId": match_id} for match_id in match_ids]
        except Exception as e:
            # Log error and return empty list
            logger.error("match_history_fetch_error", puuid=puuid, error=str(e))
            return []

    async def get_multiple_players_matches(
        self, puuids: List[str], count: int = 20
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get recent matches for multiple players concurrently"""
        tasks = [self.get_player_recent_matches(puuid, count) for puuid in puuids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        matches_by_player = {}
        for i, puuid in enumerate(puuids):
            if isinstance(results[i], Exception):
                matches_by_player[puuid] = []
            else:
                matches_by_player[puuid] = results[i]

        return matches_by_player

    async def get_match_participants_data(
        self, match_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Get participant data for multiple matches"""
        tasks = [self.fetch_match_data(match_id) for match_id in match_ids]
        match_results = await asyncio.gather(*tasks, return_exceptions=True)

        participants_data = []
        for i, match_id in enumerate(match_ids):
            if isinstance(match_results[i], Exception) or match_results[i] is None:
                continue

            match_data = match_results[i]
            # Extract participant data from match
            participants = match_data.get("info", {}).get("participants", [])
            for participant in participants:
                participants_data.append(
                    {
                        "match_id": match_id,
                        "puuid": participant.get("puuid"),
                        "summoner_id": participant.get("summonerId"),
                        "rank": participant.get("rank"),
                        "tier": participant.get("tier"),
                        "win": participant.get("win", False),
                    }
                )

        return participants_data
