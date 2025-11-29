"""Match data processor for extracting matchmaking analysis metrics."""

from typing import List, Optional, Dict, Any
import statistics
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.features.players.ranks import PlayerRank

logger = structlog.get_logger()


class MatchDataProcessor:
    """Processes raw match data to extract matchmaking metrics."""

    async def process_match_data(
        self, match_data: Dict[str, Any], player_puuid: str, db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Process a single match and extract matchmaking analysis metrics.

        Args:
            match_data: Raw match data from Riot API
            player_puuid: PUUID of the target player

        Returns:
            Dict with extracted metrics or None if processing failed
        """
        if not match_data or not isinstance(match_data, dict):
            return None

        info = match_data.get("info")
        if not info or not isinstance(info, dict):
            return None

        participants = info.get("participants", [])
        if not participants:
            return None

        # Find target player and their team
        target_player, target_team_id = self._find_target_player(participants, player_puuid)
        if not target_player or target_team_id is None:
            return None

        # Process teams and calculate metrics
        team_metrics = await self._process_team_metrics(participants, player_puuid, target_team_id, db)
        if not team_metrics:
            return None

        # Calculate rank difference
        rank_difference = self._calculate_team_rank_difference(
            team_metrics["team_ranks"], team_metrics["enemy_ranks"]
        )

        return {
            "team_winrates": team_metrics["team_winrates"],
            "enemy_winrates": team_metrics["enemy_winrates"],
            "rank_difference": rank_difference,
            "player_win": target_player.get("win", False),
        }

    def _find_target_player(
        self, participants: List[Dict[str, Any]], player_puuid: str
    ) -> tuple[Optional[Dict[str, Any]], Optional[int]]:
        """Find target player in participants list.

        Args:
            participants: List of participant data
            player_puuid: PUUID of target player

        Returns:
            Tuple of (target_player_data, team_id) or (None, None) if not found
        """
        if not participants:
            return None, None

        for participant in participants:
            if not participant or not isinstance(participant, dict):
                continue
            if participant.get("puuid") == player_puuid:
                return participant, participant.get("teamId")
        return None, None

    async def _process_team_metrics(
        self, participants: List[Dict[str, Any]], player_puuid: str, target_team_id: int, db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Process participant data to extract team metrics.

        Args:
            participants: List of participant data
            player_puuid: PUUID of target player (to skip)
            target_team_id: Team ID of target player

        Returns:
            Dict with team metrics or None if processing failed
        """
        if not participants:
            return None

        # Collect all PUUIDs first (excluding target player)
        puuids_to_fetch = [
            p.get("puuid") for p in participants
            if p and isinstance(p, dict) and p.get("puuid") and p.get("puuid") != player_puuid
        ]

        # Batch fetch all player rank data in one query
        rank_data_map = await self._batch_fetch_rank_data(puuids_to_fetch, db)

        team_winrates: List[float] = []
        enemy_winrates: List[float] = []
        team_ranks: List[int] = []
        enemy_ranks: List[int] = []

        for participant in participants:
            if not participant or not isinstance(participant, dict):
                continue
            if participant.get("puuid") == player_puuid:
                continue  # Skip target player

            participant_puuid = participant.get("puuid")
            if not participant_puuid:
                continue

            # Use batch-fetched data instead of individual queries
            rank_info = rank_data_map.get(participant_puuid)
            participant_winrate = rank_info.get("winrate") if rank_info else None
            participant_rank = rank_info.get("numeric_rank") if rank_info else None
            participant_team_id = participant.get("teamId")

            if participant_winrate is not None:
                if participant_team_id == target_team_id:
                    team_winrates.append(participant_winrate)
                    if participant_rank is not None:
                        team_ranks.append(participant_rank)
                else:
                    enemy_winrates.append(participant_winrate)
                    if participant_rank is not None:
                        enemy_ranks.append(participant_rank)

        return {
            "team_winrates": team_winrates,
            "enemy_winrates": enemy_winrates,
            "team_ranks": team_ranks,
            "enemy_ranks": enemy_ranks,
        }

    async def _batch_fetch_rank_data(
        self, puuids: List[str], db: AsyncSession
    ) -> Dict[str, Dict[str, Any]]:
        """Batch fetch rank data for multiple players in one query.

        Args:
            puuids: List of player PUUIDs
            db: Database session

        Returns:
            Dict mapping PUUID to rank info (winrate, numeric_rank)
        """
        if not puuids:
            return {}

        try:
            # Single query for all players
            stmt = select(PlayerRank).where(
                PlayerRank.puuid.in_(puuids),
                PlayerRank.queue_type == "RANKED_SOLO_5x5",
                PlayerRank.is_current == True
            )
            result = await db.execute(stmt)
            rank_records = result.scalars().all()

            # Build lookup dictionary
            rank_data_map: Dict[str, Dict[str, Any]] = {}
            for rank_data in rank_records:
                puuid = rank_data.puuid

                # Calculate winrate
                wins = rank_data.wins
                losses = rank_data.losses
                total_games = wins + losses
                winrate = wins / total_games if total_games > 0 else None

                # Calculate numeric rank
                numeric_rank = self._calculate_numeric_rank(
                    rank_data.tier, rank_data.rank, rank_data.league_points
                )

                rank_data_map[puuid] = {
                    "winrate": winrate,
                    "numeric_rank": numeric_rank,
                }

            logger.debug(
                "batch_rank_data_fetched",
                requested=len(puuids),
                found=len(rank_data_map),
            )
            return rank_data_map

        except Exception as e:
            logger.error("batch_rank_fetch_failed", error=str(e))
            return {}

    def _calculate_numeric_rank(
        self, tier: str, division: Optional[str], lp: int
    ) -> Optional[int]:
        """Calculate numeric rank value from tier, division, and LP.

        Args:
            tier: Rank tier (IRON, BRONZE, etc.)
            division: Division (I, II, III, IV) or None for Master+
            lp: League points

        Returns:
            Numeric rank value or None
        """
        tier_values = {
            "IRON": 0, "BRONZE": 400, "SILVER": 800, "GOLD": 1200,
            "PLATINUM": 1600, "EMERALD": 2000, "DIAMOND": 2400,
            "MASTER": 2800, "GRANDMASTER": 3000, "CHALLENGER": 3200,
        }

        tier_upper = tier.upper() if tier else ""
        base_rank = tier_values.get(tier_upper, 0)

        if tier_upper in ("MASTER", "GRANDMASTER", "CHALLENGER"):
            return base_rank + lp

        division_values = {"IV": 0, "III": 100, "II": 200, "I": 300}
        division_offset = division_values.get(division, 0) if division else 0

        return base_rank + division_offset + lp

    def _calculate_team_rank_difference(
        self, team_ranks: List[int], enemy_ranks: List[int]
    ) -> float:
        """Calculate rank difference between teams.

        Args:
            team_ranks: List of player ranks on target's team
            enemy_ranks: List of player ranks on enemy team

        Returns:
            Average rank difference as float
        """
        avg_team_rank = statistics.mean(team_ranks) if team_ranks else 0
        avg_enemy_rank = statistics.mean(enemy_ranks) if enemy_ranks else 0
        return abs(avg_team_rank - avg_enemy_rank)

    async def _extract_participant_winrate(self, participant_puuid: str, db: AsyncSession) -> Optional[float]:
        """Extract winrate from player_ranks table for a participant.

        Args:
            participant_puuid: PUUID of the participant

        Returns:
            Winrate as float between 0.0-1.0 or None if not available
        """
        try:
            # Query player_ranks table for RANKED_SOLO_5x5 queue
            stmt = select(PlayerRank).where(
                PlayerRank.puuid == participant_puuid,
                PlayerRank.queue_type == "RANKED_SOLO_5x5",
                PlayerRank.is_current == True
            )
            result = await db.execute(stmt)
            rank_data = result.scalar_one_or_none()

            if not rank_data:
                # Player not in database or no ranked data
                logger.debug("no_rank_data_found", puuid=participant_puuid)
                return None

            wins = rank_data.wins
            losses = rank_data.losses
            total_games = wins + losses

            if total_games == 0:
                return None

            winrate = wins / total_games
            logger.debug(
                "winrate_extracted",
                puuid=participant_puuid,
                wins=wins,
                losses=losses,
                winrate=winrate
            )
            return winrate

        except Exception as e:
            logger.error(
                "winrate_extraction_failed",
                puuid=participant_puuid,
                error=str(e)
            )
            return None

    async def _extract_participant_rank(self, participant_puuid: str, db: AsyncSession) -> Optional[int]:
        """Extract numeric rank from player_ranks table with LP-aware calculation.

        Args:
            participant_puuid: PUUID of the participant

        Returns:
            Numeric rank value or None if not available
        """
        try:
            # Query player_ranks table for RANKED_SOLO_5x5 queue
            stmt = select(PlayerRank).where(
                PlayerRank.puuid == participant_puuid,
                PlayerRank.queue_type == "RANKED_SOLO_5x5",
                PlayerRank.is_current == True
            )
            result = await db.execute(stmt)
            rank_data = result.scalar_one_or_none()

            if not rank_data:
                logger.debug("no_rank_data_for_rank_calc", puuid=participant_puuid)
                return None

            tier = rank_data.tier.upper()
            division = rank_data.rank  # Can be None for Master+
            lp = rank_data.league_points

            # Convert tier to base numeric value (each tier = 400 LP range)
            tier_values = {
                "IRON": 0,
                "BRONZE": 400,
                "SILVER": 800,
                "GOLD": 1200,
                "PLATINUM": 1600,
                "EMERALD": 2000,
                "DIAMOND": 2400,
                "MASTER": 2800,
                "GRANDMASTER": 3000,
                "CHALLENGER": 3200,
            }

            base_rank = tier_values.get(tier, 0)

            # For Master+, there are no divisions, just add LP directly
            if tier in ("MASTER", "GRANDMASTER", "CHALLENGER"):
                numeric_rank = base_rank + lp
                logger.debug(
                    "rank_calculated_master_plus",
                    puuid=participant_puuid,
                    tier=tier,
                    lp=lp,
                    numeric_rank=numeric_rank
                )
                return numeric_rank

            # For Iron-Diamond, each division is 100 LP
            # Division IV = 0, III = 100, II = 200, I = 300
            division_values = {"IV": 0, "III": 100, "II": 200, "I": 300}
            division_offset = division_values.get(division, 0) if division else 0

            # Add division offset + LP (0-100)
            numeric_rank = base_rank + division_offset + lp

            logger.debug(
                "rank_calculated",
                puuid=participant_puuid,
                tier=tier,
                division=division,
                lp=lp,
                numeric_rank=numeric_rank
            )
            return numeric_rank

        except Exception as e:
            logger.error(
                "rank_extraction_failed",
                puuid=participant_puuid,
                error=str(e)
            )
            return None