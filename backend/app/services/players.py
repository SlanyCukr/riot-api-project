"""Player service for handling player data operations."""

from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_

from ..riot_api.data_manager import RiotDataManager
from ..riot_api.errors import RateLimitError, NotFoundError
from ..models.players import Player
from ..schemas.players import PlayerResponse, PlayerUpdate
from ..config import get_global_settings
import structlog

logger = structlog.get_logger(__name__)


class PlayerService:
    """Service for handling player data operations."""

    def __init__(self, db: AsyncSession, riot_data_manager: RiotDataManager):
        """Initialize player service with database and data manager."""
        self.db = db
        self.data_manager = riot_data_manager

    async def get_player_by_riot_id(
        self, game_name: str, tag_line: str, platform: str
    ) -> PlayerResponse:
        """Get player by Riot ID (name#tag) using intelligent data management."""
        try:
            # Validate platform
            valid_platforms = [
                "eun1",
                "euw1",
                "na1",
                "kr",
                "br1",
                "la1",
                "la2",
                "oc1",
                "ru",
                "tr1",
                "jp1",
                "ph2",
                "sg2",
                "th2",
                "tw2",
                "vn2",
            ]
            if platform not in valid_platforms:
                raise ValueError(
                    f"Invalid platform: {platform}. Must be one of: {', '.join(valid_platforms)}"
                )

            # Use RiotDataManager for intelligent data fetching
            player_response = await self.data_manager.get_player_by_riot_id(
                game_name, tag_line, platform
            )

            if not player_response:
                raise ValueError(f"Player not found: {game_name}#{tag_line}")

            logger.info(
                "Player data retrieved successfully",
                extra={
                    "game_name": game_name,
                    "tag_line": tag_line,
                    "platform": platform,
                },
            )

            return player_response

        except RateLimitError as e:
            logger.warning(
                "Rate limit hit while fetching player",
                extra={
                    "game_name": game_name,
                    "tag_line": tag_line,
                    "retry_after": e.retry_after,
                },
            )
            raise

        except NotFoundError:
            # Player not found in Riot API - convert to ValueError for API layer
            raise ValueError(f"Player not found: {game_name}#{tag_line}")

        except ValueError:
            # Re-raise validation errors
            raise

        except Exception as e:
            logger.error(
                "Failed to fetch player data",
                extra={
                    "game_name": game_name,
                    "tag_line": tag_line,
                    "platform": platform,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise Exception(f"Failed to fetch player data: {str(e)}")

    async def get_player_by_summoner_name(
        self, summoner_name: str, platform: str
    ) -> PlayerResponse:
        """
        Get player by summoner name from database only.

        This searches only the local database for players already being tracked.
        To add new players from Riot API, use a separate add/import feature.
        """
        # Search database for exact match or partial match
        result = await self.db.execute(
            select(Player).where(
                Player.summoner_name.ilike(f"%{summoner_name}%"),
                Player.platform == platform,
                Player.is_active,
            )
        )
        players = result.scalars().all()

        # If exact match found, return it
        for player in players:
            if (
                player.summoner_name
                and player.summoner_name.lower() == summoner_name.lower()
            ):
                logger.info(
                    "Found exact match for summoner name",
                    summoner_name=summoner_name,
                    platform=platform,
                )
                return PlayerResponse.model_validate(player)

        # If only one partial match, return it
        if len(players) == 1:
            logger.info(
                "Found single partial match for summoner name",
                summoner_name=summoner_name,
                platform=platform,
                matched_name=players[0].summoner_name,
            )
            return PlayerResponse.model_validate(players[0])

        # If multiple partial matches, return error with suggestions
        if len(players) > 1:
            matched_names = [p.summoner_name for p in players if p.summoner_name]
            logger.info(
                "Found multiple matches for summoner name",
                summoner_name=summoner_name,
                platform=platform,
                matches=matched_names,
            )
            raise ValueError(
                f"Multiple players found matching '{summoner_name}': {', '.join(matched_names)}. "
                "Please be more specific."
            )

        # No matches found in database
        logger.info(
            "No player found in database for summoner name",
            summoner_name=summoner_name,
            platform=platform,
        )
        raise ValueError(f"Player not found: {summoner_name}")

    async def get_player_by_puuid(
        self, puuid: str, platform: str = "eun1"
    ) -> PlayerResponse:
        """Get player by PUUID using intelligent data management."""
        try:
            player_response = await self.data_manager.get_player_by_puuid(
                puuid, platform
            )

            if not player_response:
                raise ValueError(f"Player not found: {puuid}")

            logger.info(
                "Player data retrieved by PUUID successfully",
                puuid=puuid,
                platform=platform,
            )

            return player_response

        except RateLimitError as e:
            logger.warning(
                "Rate limit hit while fetching player by PUUID",
                puuid=puuid,
                retry_after=e.retry_after,
            )
            raise

        except Exception as e:
            logger.error(
                "Failed to fetch player data by PUUID",
                puuid=puuid,
                platform=platform,
                error=str(e),
            )
            raise Exception(f"Failed to fetch player data: {str(e)}")

    async def get_recent_opponents_with_details(
        self, puuid: str, limit: int
    ) -> List[PlayerResponse]:
        """
        Get recent opponents for a player with their details from database only.
        Only returns players that exist in our database with summoner_name populated.
        Does NOT make any Riot API calls.

        Args:
            puuid: Player PUUID
            limit: Maximum number of unique opponents to return

        Returns:
            List of PlayerResponse objects for opponents found in database
        """
        try:
            from ..models.participants import MatchParticipant

            # Subquery to get recent match IDs for this player
            player_matches_stmt = (
                select(MatchParticipant.match_id)
                .where(MatchParticipant.puuid == puuid)
                .order_by(MatchParticipant.id.desc())
                .limit(limit * 5)  # Get more matches to find enough opponents
            )
            player_match_ids = (
                (await self.db.execute(player_matches_stmt)).scalars().all()
            )

            if not player_match_ids:
                logger.debug("No matches found for player", puuid=puuid)
                return []

            # Query for opponent PUUIDs from those matches
            opponents_puuids_stmt = (
                select(MatchParticipant.puuid)
                .where(
                    and_(
                        MatchParticipant.match_id.in_(player_match_ids),
                        MatchParticipant.puuid != puuid,
                    )
                )
                .distinct()
            )
            opponent_puuids = (
                (await self.db.execute(opponents_puuids_stmt)).scalars().all()
            )

            if not opponent_puuids:
                logger.debug("No opponents found for player", puuid=puuid)
                return []

            # Fetch full player details from database only
            # Filter to only players with summoner_name populated (not null and not empty)
            players_stmt = (
                select(Player)
                .where(
                    and_(
                        Player.puuid.in_(opponent_puuids),
                        Player.is_active,
                        Player.summoner_name.isnot(None),
                        Player.summoner_name != "",
                    )
                )
                .limit(limit)
            )

            result = await self.db.execute(players_stmt)
            players = result.scalars().all()

            logger.debug(
                "Found recent opponents with details",
                puuid=puuid,
                opponent_count=len(players),
                limit=limit,
            )

            return [PlayerResponse.model_validate(player) for player in players]

        except Exception as e:
            logger.error(
                "Failed to get recent opponents with details",
                puuid=puuid,
                error=str(e),
            )
            # Return empty list instead of raising to not break the UI
            return []

    async def _update_player(
        self, puuid: UUID, update_data: PlayerUpdate
    ) -> Optional[Player]:
        """Update existing player record."""
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return None

        update_dict["updated_at"] = datetime.now(timezone.utc)
        if "last_seen" not in update_dict:
            update_dict["last_seen"] = datetime.now(timezone.utc)

        stmt = (
            update(Player)
            .where(Player.puuid == puuid)
            .values(**update_dict)
            .returning(Player)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def bulk_get_players(self, puuids: List[str]) -> List[PlayerResponse]:
        """Get multiple players by PUUIDs."""
        if not puuids:
            return []

        result = await self.db.execute(
            select(Player).where(Player.puuid.in_(puuids), Player.is_active)
        )
        players = result.scalars().all()
        return [PlayerResponse.model_validate(player) for player in players]

    async def search_players(
        self,
        summoner_name: Optional[str] = None,
        riot_id: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 20,
    ) -> List[PlayerResponse]:
        """Search players by various criteria."""
        query = select(Player).where(Player.is_active)

        if summoner_name:
            query = query.where(Player.summoner_name.ilike(f"%{summoner_name}%"))

        if riot_id:
            if "#" in riot_id:
                game_name, tag_line = riot_id.split("#", 1)
                query = query.where(
                    Player.riot_id.ilike(f"%{game_name}%"),
                    Player.tag_line.ilike(f"%{tag_line}%"),
                )
            else:
                query = query.where(Player.riot_id.ilike(f"%{riot_id}%"))

        if platform:
            query = query.where(Player.platform == platform)

        query = query.limit(limit)

        result = await self.db.execute(query)
        players = result.scalars().all()
        return [PlayerResponse.model_validate(player) for player in players]

    # === Player Tracking Methods for Automated Jobs ===

    async def track_player(self, puuid: str) -> PlayerResponse:
        """Mark a player as tracked for automated monitoring.

        Args:
            puuid: Player's PUUID to track.

        Returns:
            Updated player data.

        Raises:
            ValueError: If player not found or tracking limit reached.
        """
        settings = get_global_settings()

        # Check current tracked player count
        tracked_count = await self.count_tracked_players()
        if tracked_count >= settings.max_tracked_players:
            raise ValueError(
                f"Maximum tracked players limit reached ({settings.max_tracked_players}). "
                f"Please untrack a player before adding a new one."
            )

        # Update player to tracked status
        stmt = (
            update(Player)
            .where(Player.puuid == puuid)
            .where(Player.is_active)
            .values(is_tracked=True, updated_at=datetime.now(timezone.utc))
            .returning(Player)
        )

        result = await self.db.execute(stmt)
        player = result.scalar_one_or_none()

        if not player:
            raise ValueError(f"Player not found: {puuid}")

        await self.db.commit()

        logger.info(
            "Player marked as tracked",
            puuid=puuid,
            summoner_name=player.summoner_name,
            tracked_count=tracked_count + 1,
        )

        return PlayerResponse.model_validate(player)

    async def untrack_player(self, puuid: str) -> PlayerResponse:
        """Remove a player from tracked status.

        Args:
            puuid: Player's PUUID to untrack.

        Returns:
            Updated player data.

        Raises:
            ValueError: If player not found.
        """
        stmt = (
            update(Player)
            .where(Player.puuid == puuid)
            .where(Player.is_active)
            .values(is_tracked=False, updated_at=datetime.now(timezone.utc))
            .returning(Player)
        )

        result = await self.db.execute(stmt)
        player = result.scalar_one_or_none()

        if not player:
            raise ValueError(f"Player not found: {puuid}")

        await self.db.commit()

        logger.info(
            "Player unmarked as tracked",
            puuid=puuid,
            summoner_name=player.summoner_name,
        )

        return PlayerResponse.model_validate(player)

    async def get_tracked_players(self) -> List[PlayerResponse]:
        """Get all players currently marked for tracking.

        Returns:
            List of tracked players.
        """
        query = (
            select(Player)
            .where(Player.is_tracked)
            .where(Player.is_active)
            .order_by(Player.summoner_name)
        )

        result = await self.db.execute(query)
        players = result.scalars().all()

        return [PlayerResponse.model_validate(player) for player in players]

    async def count_tracked_players(self) -> int:
        """Get count of currently tracked players.

        Returns:
            Number of tracked players.
        """
        query = (
            select(func.count())
            .select_from(Player)
            .where(Player.is_tracked, Player.is_active)
        )

        result = await self.db.execute(query)
        return result.scalar() or 0

    # === Methods for Player Analyzer Job ===

    async def get_players_needing_matches(
        self, limit: int, target_matches: int
    ) -> List[Player]:
        """
        Get discovered players with insufficient match history.

        This is used by the player analyzer job to find players that need
        more matches fetched before they can be analyzed.

        Args:
            limit: Maximum number of players to return
            target_matches: Target number of matches per player

        Returns:
            List of Player objects needing match data
        """
        from ..models.participants import MatchParticipant

        stmt = (
            select(Player)
            .join(
                MatchParticipant, Player.puuid == MatchParticipant.puuid, isouter=True
            )
            .where(Player.is_tracked.is_(False))
            .where(Player.is_active.is_(True))
            .group_by(Player.puuid)
            .having(func.count(MatchParticipant.match_id) < target_matches)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.debug(
            "Found players needing matches",
            count=len(players),
            target_matches=target_matches,
        )

        return players

    async def get_players_ready_for_analysis(
        self, limit: int, min_matches: int = 20
    ) -> List[Player]:
        """
        Get unanalyzed players with sufficient match history for smurf detection.

        This is used by the player analyzer job to find players ready for
        smurf detection analysis.

        Args:
            limit: Maximum number of players to return
            min_matches: Minimum number of matches required for analysis

        Returns:
            List of Player objects ready for analysis
        """
        from ..models.participants import MatchParticipant

        stmt = (
            select(Player)
            .join(MatchParticipant, Player.puuid == MatchParticipant.puuid)
            .where(Player.is_tracked.is_(False))
            .where(Player.is_analyzed.is_(False))
            .where(Player.is_active.is_(True))
            .group_by(Player.puuid)
            .having(func.count(MatchParticipant.match_id) >= min_matches)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.debug(
            "Found players ready for analysis",
            count=len(players),
            min_matches=min_matches,
        )

        return players

    async def get_players_for_ban_check(
        self, days: int, limit: int = 10
    ) -> List[Player]:
        """
        Get detected smurfs that need ban status checking.

        This is used by the player analyzer job to find players that were
        previously detected as smurfs and haven't had their ban status checked
        recently.

        Args:
            days: Number of days since last ban check
            limit: Maximum number of players to return

        Returns:
            List of Player objects needing ban check
        """
        from ..models.smurf_detection import SmurfDetection
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=days)

        stmt = (
            select(Player)
            .join(SmurfDetection, Player.puuid == SmurfDetection.puuid)
            .where(SmurfDetection.is_smurf.is_(True))
            .where(
                or_(
                    Player.last_ban_check.is_(None), Player.last_ban_check < cutoff
                )
            )
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.debug(
            "Found players needing ban check",
            count=len(players),
            days_since_last_check=days,
        )

        return players

    async def check_ban_status(self, player: Player) -> bool:
        """
        Check if a player is banned by attempting to fetch their summoner data.

        A 404 response from the Riot API typically indicates the player is banned
        or has changed their name.

        Args:
            player: Player object to check

        Returns:
            True if player is likely banned, False if player is active
        """
        from ..riot_api.endpoints import Platform
        from ..riot_api.errors import NotFoundError
        from datetime import datetime

        try:
            platform = Platform(player.platform.lower())

            # Attempt to fetch summoner data
            await self.data_manager.api_client.get_summoner_by_puuid(
                player.puuid, platform
            )

            # Player found = not banned
            player.last_ban_check = datetime.now()
            await self.db.commit()

            logger.debug("Player is active (not banned)", puuid=player.puuid)
            return False

        except NotFoundError:
            # 404 = player not found, likely banned or name changed
            player.last_ban_check = datetime.now()
            await self.db.commit()

            logger.info("Player likely banned (404 from API)", puuid=player.puuid)
            return True

        except ValueError:
            # Invalid platform
            logger.warning("Invalid platform for ban check", puuid=player.puuid)
            return False

        except Exception as e:
            # Other errors - log and return False to avoid false positives
            logger.warning(
                "Ban check failed with error",
                puuid=player.puuid,
                error=str(e),
            )
            return False
