"""Matchmaking analysis service for analyzing League of Legends matchmaking fairness."""

import asyncio
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from ..models.matchmaking_analysis import MatchmakingAnalysis, AnalysisStatus
from ..models.matches import Match
from ..models.participants import MatchParticipant
from ..schemas.matchmaking import (
    MatchmakingAnalysisResponse,
    MatchmakingAnalysisStatusResponse,
)
from app.core.riot_api.client import RiotAPIClient
from app.core.riot_api.errors import RiotAPIError
from app.core.riot_api.transformers import MatchTransformer

logger = structlog.get_logger(__name__)


class MatchmakingAnalysisService:
    """Service for analyzing matchmaking fairness."""

    def __init__(self, db: AsyncSession, riot_client: RiotAPIClient):
        """Initialize matchmaking analysis service."""
        self.db = db
        self.riot_client = riot_client
        self.transformer = MatchTransformer()
        self._cancel_flags: Dict[int, bool] = {}  # Track cancellation requests

    async def start_analysis(self, puuid: str) -> MatchmakingAnalysisResponse:
        """
        Start a new matchmaking analysis for a player.

        Args:
            puuid: Player PUUID to analyze

        Returns:
            MatchmakingAnalysisResponse with analysis ID and initial status
        """
        # Check if there's already an active analysis for this player
        result = await self.db.execute(
            select(MatchmakingAnalysis)
            .where(
                MatchmakingAnalysis.puuid == puuid,
                MatchmakingAnalysis.status.in_(
                    [AnalysisStatus.PENDING.value, AnalysisStatus.IN_PROGRESS.value]
                ),
            )
            .order_by(MatchmakingAnalysis.created_at.desc())
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(
                "Found existing active analysis",
                analysis_id=existing.id,
                puuid=puuid,
                status=existing.status,
            )
            return MatchmakingAnalysisResponse.model_validate(existing)

        # Create new analysis record
        # Initialize with 0 progress but also 0 total to avoid showing misleading "0 of 1000"
        # Will be updated once we fetch the player's matches
        analysis = MatchmakingAnalysis(
            puuid=puuid,
            status=AnalysisStatus.PENDING.value,
            progress=0,
            total_requests=0,  # Will be calculated after fetching matches
            estimated_minutes_remaining=0,  # Will be calculated after fetching matches
        )

        self.db.add(analysis)
        await self.db.commit()
        await self.db.refresh(analysis)

        logger.info(
            "Created new matchmaking analysis", analysis_id=analysis.id, puuid=puuid
        )

        # Start analysis in background
        asyncio.create_task(self._run_analysis(analysis.id, puuid))

        return MatchmakingAnalysisResponse.model_validate(analysis)

    async def get_analysis_status(
        self, analysis_id: int
    ) -> Optional[MatchmakingAnalysisStatusResponse]:
        """Get current status of an analysis."""
        result = await self.db.execute(
            select(MatchmakingAnalysis).where(MatchmakingAnalysis.id == analysis_id)
        )
        analysis = result.scalar_one_or_none()

        if not analysis:
            return None

        return MatchmakingAnalysisStatusResponse.model_validate(analysis)

    async def get_latest_analysis(
        self, puuid: str
    ) -> Optional[MatchmakingAnalysisResponse]:
        """Get the latest analysis for a player."""
        result = await self.db.execute(
            select(MatchmakingAnalysis)
            .where(MatchmakingAnalysis.puuid == puuid)
            .order_by(MatchmakingAnalysis.created_at.desc())
            .limit(1)
        )
        analysis = result.scalar_one_or_none()

        if not analysis:
            return None

        return MatchmakingAnalysisResponse.model_validate(analysis)

    async def cancel_analysis(self, analysis_id: int) -> bool:
        """
        Cancel an ongoing analysis.

        Args:
            analysis_id: ID of the analysis to cancel

        Returns:
            True if cancelled successfully, False if not found or already complete
        """
        result = await self.db.execute(
            select(MatchmakingAnalysis).where(MatchmakingAnalysis.id == analysis_id)
        )
        analysis = result.scalar_one_or_none()

        if not analysis:
            return False

        if analysis.status in [
            AnalysisStatus.COMPLETED.value,
            AnalysisStatus.FAILED.value,
            AnalysisStatus.CANCELLED.value,
        ]:
            return False

        # Set cancel flag
        self._cancel_flags[analysis_id] = True

        # Update status
        await self.db.execute(
            update(MatchmakingAnalysis)
            .where(MatchmakingAnalysis.id == analysis_id)
            .values(
                status=AnalysisStatus.CANCELLED.value,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self.db.commit()

        logger.info("Analysis cancelled", analysis_id=analysis_id)
        return True

    async def _run_analysis(self, analysis_id: int, puuid: str) -> None:
        """
        Run the matchmaking analysis in the background.

        This method implements the core analysis logic:
        1. Fetch player's last 10 matches
        2. For each match, get 10 participants
        3. For each participant, get their last 10 matches
        4. Calculate average winrates for same team vs enemy team
        """
        try:
            logger.info(
                "Starting matchmaking analysis", analysis_id=analysis_id, puuid=puuid
            )

            # Step 1: Get player's last 10 matches
            player_matches = await self._fetch_player_matches(puuid, count=10)

            if self._is_cancelled(analysis_id):
                return

            if not player_matches:
                raise ValueError("No matches found for player")

            logger.info(
                "Fetched player matches",
                analysis_id=analysis_id,
                match_count=len(player_matches),
            )

            # Calculate total estimated requests
            # 1 for initial match list + (10 matches * 11 requests per match)
            # Each match: 1 for participants + 10 for each participant's history and matches
            total_estimated = 1 + (len(player_matches) * 11)

            # Update status to in progress with accurate totals
            await self.db.execute(
                update(MatchmakingAnalysis)
                .where(MatchmakingAnalysis.id == analysis_id)
                .values(
                    status=AnalysisStatus.IN_PROGRESS.value,
                    started_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    progress=1,  # We've completed the initial fetch
                    total_requests=total_estimated,
                    estimated_minutes_remaining=total_estimated
                    // 50,  # ~50 requests per minute
                )
            )
            await self.db.commit()

            # Step 2-5: Process each match and calculate winrates
            results = await self._analyze_matches(analysis_id, puuid, player_matches)

            if self._is_cancelled(analysis_id):
                logger.info(
                    "Analysis cancelled after processing",
                    analysis_id=analysis_id,
                )
                return

            # Check if results are empty (might indicate cancellation)
            if not results or not results.get("matches_analyzed"):
                logger.warning(
                    "No results from analysis (may have been cancelled)",
                    analysis_id=analysis_id,
                )
                return

            # Store results
            await self.db.execute(
                update(MatchmakingAnalysis)
                .where(MatchmakingAnalysis.id == analysis_id)
                .values(
                    status=AnalysisStatus.COMPLETED.value,
                    results=results,
                    completed_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    estimated_minutes_remaining=0,
                )
            )
            await self.db.commit()

            logger.info(
                "Matchmaking analysis completed",
                analysis_id=analysis_id,
                results=results,
            )

        except Exception as e:
            logger.error(
                "Matchmaking analysis failed",
                analysis_id=analysis_id,
                error=str(e),
                exc_info=True,
            )

            # Update status to failed
            await self.db.execute(
                update(MatchmakingAnalysis)
                .where(MatchmakingAnalysis.id == analysis_id)
                .values(
                    status=AnalysisStatus.FAILED.value,
                    error_message=str(e),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await self.db.commit()

        finally:
            # Clean up cancel flag
            self._cancel_flags.pop(analysis_id, None)

    def _is_cancelled(self, analysis_id: int) -> bool:
        """Check if analysis has been cancelled."""
        return self._cancel_flags.get(analysis_id, False)

    async def _fetch_player_matches(self, puuid: str, count: int = 10) -> List[str]:
        """
        Fetch player's last N match IDs.

        Checks DB first for existing matches, then fetches from API for any missing ones.
        """
        # Check DB for existing ranked matches
        result = await self.db.execute(
            select(MatchParticipant.match_id)
            .join(Match, MatchParticipant.match_id == Match.match_id)
            .where(
                MatchParticipant.puuid == puuid,
                Match.queue_id == 420,  # Ranked Solo/Duo only
            )
            .order_by(Match.game_creation.desc())
            .limit(count)
        )
        db_matches = [row[0] for row in result.all()]

        logger.info(
            "Found matches in DB",
            puuid=puuid,
            count=len(db_matches),
            requested=count,
        )

        # If we have enough matches in DB, use those
        if len(db_matches) >= count:
            return db_matches[:count]

        # Otherwise, fetch from API to get the latest
        try:
            match_list = await self.riot_client.get_match_list_by_puuid(
                puuid=puuid,
                start=0,
                count=count,
                queue=420,  # Ranked Solo/Duo only
            )

            logger.info(
                "Fetched matches from API",
                puuid=puuid,
                count=len(match_list.match_ids),
            )

            return match_list.match_ids
        except RiotAPIError as e:
            logger.error(
                "Failed to fetch player matches from API",
                puuid=puuid,
                error=str(e),
            )
            # If API fails but we have some DB matches, return those
            if db_matches:
                logger.warning(
                    "Using DB matches due to API failure",
                    puuid=puuid,
                    count=len(db_matches),
                )
                return db_matches
            raise

    async def _get_match_participants(self, match_id: str) -> List[Tuple[str, int]]:
        """
        Get list of (puuid, team_id) tuples for a match.

        Checks DB first, fetches from API if not found.

        Returns:
            List of (puuid, team_id) tuples
        """
        # Check database first
        result = await self.db.execute(
            select(MatchParticipant.puuid, MatchParticipant.team_id).where(
                MatchParticipant.match_id == match_id
            )
        )
        participants = result.all()

        if participants:
            logger.debug(
                "Found match participants in DB",
                match_id=match_id,
                count=len(participants),
            )
            return [(p.puuid, p.team_id) for p in participants]

        # Not in DB, fetch from API
        logger.info("Fetching match from API", match_id=match_id)

        try:
            match_dto = await self.riot_client.get_match(match_id)

            # Store match in database
            await self._store_match(match_dto)

            # Extract participants
            participants = []
            for participant_data in match_dto.info.participants:
                participants.append((participant_data.puuid, participant_data.team_id))

            return participants

        except RiotAPIError as e:
            logger.error(
                "Failed to fetch match",
                match_id=match_id,
                error=str(e),
            )
            raise

    async def _store_match(self, match_dto) -> None:
        """Store match and participants in database."""
        try:
            # Convert MatchDTO to dict for transformer
            match_data_dict = {
                "metadata": {
                    "matchId": match_dto.metadata.match_id,
                },
                "info": {
                    "platformId": match_dto.info.platform_id,
                    "gameCreation": match_dto.info.game_creation,
                    "gameDuration": match_dto.info.game_duration,
                    "queueId": match_dto.info.queue_id,
                    "gameVersion": match_dto.info.game_version,
                    "mapId": match_dto.info.map_id,
                    "gameMode": match_dto.info.game_mode,
                    "gameType": match_dto.info.game_type,
                    "gameEndTimestamp": match_dto.info.game_end_timestamp,
                    "tournamentId": getattr(match_dto.info, "tournament_code", None),
                    "participants": [
                        {
                            "puuid": p.puuid,
                            "summonerName": p.summoner_name,
                            "teamId": p.team_id,
                            "championId": p.champion_id,
                            "championName": p.champion_name,
                            "kills": p.kills,
                            "deaths": p.deaths,
                            "assists": p.assists,
                            "win": p.win,
                            "goldEarned": p.gold_earned,
                            "visionScore": p.vision_score,
                            "totalMinionsKilled": getattr(p, "total_minions_killed", 0),
                            "neutralMinionsKilled": getattr(
                                p, "neutral_minions_killed", 0
                            ),
                            "champLevel": p.champ_level,
                            "totalDamageDealt": p.total_damage_dealt,
                            "totalDamageDealtToChampions": p.total_damage_dealt_to_champions,
                            "damageTaken": p.total_damage_taken,
                            "totalHeal": p.total_heal,
                            "individualPosition": p.individual_position,
                            "teamPosition": p.team_position,
                            "role": p.role,
                        }
                        for p in match_dto.info.participants
                    ],
                },
            }

            # Transform data
            transformed = self.transformer.transform_match_data(match_data_dict)

            # Upsert match
            match_stmt = (
                insert(Match)
                .values(**transformed["match"])
                .on_conflict_do_nothing(index_elements=["match_id"])
            )
            await self.db.execute(match_stmt)

            # Upsert participants
            for participant_dict in transformed["participants"]:
                participant_stmt = (
                    insert(MatchParticipant)
                    .values(**participant_dict)
                    .on_conflict_do_nothing(index_elements=["match_id", "puuid"])
                )
                await self.db.execute(participant_stmt)

            await self.db.commit()

        except Exception as e:
            logger.error(
                "Failed to store match",
                match_id=match_dto.metadata.match_id,
                error=str(e),
            )
            await self.db.rollback()
            # Don't raise - this is a background task and we can continue

    async def _get_participant_winrate(
        self, puuid: str, match_id: str
    ) -> Optional[bool]:
        """
        Get win status for a participant in a match.

        Checks DB first, fetches from API if not found.

        Returns:
            True if won, False if lost, None if not found
        """
        # Check database first
        result = await self.db.execute(
            select(MatchParticipant.win).where(
                MatchParticipant.match_id == match_id,
                MatchParticipant.puuid == puuid,
            )
        )
        win_status = result.scalar_one_or_none()

        if win_status is not None:
            return win_status

        # Not in DB, need to fetch match
        try:
            match_dto = await self.riot_client.get_match(match_id)
            await self._store_match(match_dto)

            # Find participant in match
            for participant_data in match_dto.info.participants:
                if participant_data.puuid == puuid:
                    return participant_data.win

            return None

        except RiotAPIError as e:
            logger.warning(
                "Failed to get participant winrate",
                puuid=puuid,
                match_id=match_id,
                error=str(e),
            )
            return None

    async def _mark_match_processed(self, match_id: str) -> None:
        """Mark a match as processed after analyzing all its participants."""
        try:
            await self.db.execute(
                update(Match)
                .where(Match.match_id == match_id)
                .values(is_processed=True)
            )
            await self.db.commit()
            logger.debug("Marked match as processed", match_id=match_id)
        except Exception as e:
            logger.warning(
                "Failed to mark match as processed",
                match_id=match_id,
                error=str(e),
            )
            await self.db.rollback()
            # Don't raise - this is not critical for analysis

    async def _analyze_matches(
        self, analysis_id: int, target_puuid: str, match_ids: List[str]
    ) -> Dict:
        """
        Analyze all matches and calculate team vs enemy winrates.

        Returns:
            Dict with team_avg_winrate, enemy_avg_winrate, matches_analyzed
        """
        team_winrates: List[float] = []
        enemy_winrates: List[float] = []

        requests_completed = 1  # Initial match list fetch
        total_estimated = len(match_ids) * 11  # Each match + 10 participants

        for match_idx, match_id in enumerate(match_ids):
            if self._is_cancelled(analysis_id):
                logger.info(
                    "Analysis cancelled during execution", analysis_id=analysis_id
                )
                return {}

            logger.info(
                f"Processing match {match_idx + 1}/{len(match_ids)}",
                analysis_id=analysis_id,
                match_id=match_id,
            )

            # Process single match
            match_result = await self._process_single_match(
                analysis_id,
                match_id,
                target_puuid,
                requests_completed,
                total_estimated,
            )

            if match_result is None:
                # Cancelled or target player not found
                if self._is_cancelled(analysis_id):
                    return {}
                continue

            # Update counters and collect winrates
            requests_completed = match_result["requests_completed"]
            team_winrates.extend(match_result["team_winrates"])
            enemy_winrates.extend(match_result["enemy_winrates"])

            # Mark this match as processed after analyzing all its participants
            await self._mark_match_processed(match_id)

        return self._calculate_final_results(
            team_winrates, enemy_winrates, len(match_ids)
        )

    async def _process_single_match(
        self,
        analysis_id: int,
        match_id: str,
        target_puuid: str,
        requests_completed: int,
        total_estimated: int,
    ) -> Optional[Dict]:
        """
        Process a single match and collect winrates for team and enemy participants.

        Args:
            analysis_id: ID of the analysis
            match_id: Match ID to process
            target_puuid: PUUID of the target player
            requests_completed: Number of requests completed so far
            total_estimated: Total estimated requests

        Returns:
            Dict with requests_completed, team_winrates, enemy_winrates, or None if cancelled/invalid
        """
        # Get participants for this match
        participants = await self._get_match_participants(match_id)
        requests_completed += 1

        # Find target player's team
        target_team_id = self._find_target_team_id(participants, target_puuid)

        if target_team_id is None:
            logger.warning(
                "Target player not found in match",
                match_id=match_id,
                target_puuid=target_puuid,
            )
            return None

        # Process each participant
        team_winrates: List[float] = []
        enemy_winrates: List[float] = []

        for participant_puuid, team_id in participants:
            if participant_puuid == target_puuid:
                continue  # Skip the target player themselves

            if self._is_cancelled(analysis_id):
                return None

            # Get participant's winrate
            winrate = await self._calculate_participant_winrate(participant_puuid)
            requests_completed += 1

            # Update progress
            await self._update_progress(
                analysis_id, requests_completed, total_estimated
            )

            # Categorize winrate by team
            self._categorize_winrate(
                winrate, team_id, target_team_id, team_winrates, enemy_winrates
            )

        return {
            "requests_completed": requests_completed,
            "team_winrates": team_winrates,
            "enemy_winrates": enemy_winrates,
        }

    def _find_target_team_id(
        self, participants: List[Tuple[str, int]], target_puuid: str
    ) -> Optional[int]:
        """
        Find the team ID of the target player in a list of participants.

        Args:
            participants: List of (puuid, team_id) tuples
            target_puuid: PUUID of the target player

        Returns:
            Team ID if found, None otherwise
        """
        for puuid, team_id in participants:
            if puuid == target_puuid:
                return team_id
        return None

    def _categorize_winrate(
        self,
        winrate: Optional[float],
        team_id: int,
        target_team_id: int,
        team_winrates: List[float],
        enemy_winrates: List[float],
    ) -> None:
        """
        Categorize a participant's winrate as either team or enemy.

        Args:
            winrate: Participant's winrate (0.0-1.0) or None
            team_id: Participant's team ID
            target_team_id: Target player's team ID
            team_winrates: List to append team winrates to (modified in place)
            enemy_winrates: List to append enemy winrates to (modified in place)
        """
        if winrate is not None:
            if team_id == target_team_id:
                team_winrates.append(winrate)
            else:
                enemy_winrates.append(winrate)

    def _calculate_final_results(
        self,
        team_winrates: List[float],
        enemy_winrates: List[float],
        matches_analyzed: int,
    ) -> Dict:
        """
        Calculate final analysis results from collected winrates.

        Args:
            team_winrates: List of winrates for teammates
            enemy_winrates: List of winrates for enemies
            matches_analyzed: Number of matches analyzed

        Returns:
            Dict with team_avg_winrate, enemy_avg_winrate, matches_analyzed
        """
        team_avg = sum(team_winrates) / len(team_winrates) if team_winrates else 0.0
        enemy_avg = sum(enemy_winrates) / len(enemy_winrates) if enemy_winrates else 0.0

        return {
            "team_avg_winrate": round(team_avg, 4),
            "enemy_avg_winrate": round(enemy_avg, 4),
            "matches_analyzed": matches_analyzed,
        }

    def _calculate_winrate_from_results(
        self, win_results: List[Tuple[bool]]
    ) -> Optional[float]:
        """
        Calculate winrate from a list of win/loss results.

        Args:
            win_results: List of tuples containing win status

        Returns:
            Float between 0.0 and 1.0, or None if empty
        """
        if not win_results:
            return None

        wins = sum(1 for (win,) in win_results if win)
        total = len(win_results)
        return wins / total if total > 0 else None

    async def _get_db_winrate(
        self, puuid: str, match_count: int
    ) -> Tuple[Optional[float], List[Tuple[bool]]]:
        """
        Get winrate from database for a participant.

        Args:
            puuid: Player PUUID
            match_count: Number of matches to check

        Returns:
            Tuple of (winrate if enough matches, all DB results for fallback)
        """
        result = await self.db.execute(
            select(MatchParticipant.win)
            .join(Match, MatchParticipant.match_id == Match.match_id)
            .where(
                MatchParticipant.puuid == puuid,
                Match.queue_id == 420,  # Ranked Solo/Duo only
            )
            .order_by(Match.game_creation.desc())
            .limit(match_count)
        )
        db_wins = result.all()

        # Return winrate if we have enough matches, otherwise return None and the partial results
        if len(db_wins) >= match_count:
            winrate = self._calculate_winrate_from_results(db_wins)
            logger.debug(
                "Calculated winrate from DB",
                puuid=puuid,
                wins=sum(1 for (win,) in db_wins if win),
                total=len(db_wins),
                winrate=winrate,
            )
            return winrate, db_wins

        return None, db_wins

    async def _get_api_winrate(self, puuid: str, match_count: int) -> Optional[float]:
        """
        Get winrate from Riot API for a participant.

        Args:
            puuid: Player PUUID
            match_count: Number of matches to fetch

        Returns:
            Float between 0.0 and 1.0, or None if no matches found
        """
        match_list = await self.riot_client.get_match_list_by_puuid(
            puuid=puuid,
            start=0,
            count=match_count,
            queue=420,  # Ranked Solo/Duo only
        )

        if not match_list.match_ids:
            return None

        # Get win status for each match
        wins = 0
        total = 0

        for match_id in match_list.match_ids:
            win_status = await self._get_participant_winrate(puuid, match_id)
            if win_status is not None:
                total += 1
                if win_status:
                    wins += 1

        return wins / total if total > 0 else None

    async def _calculate_participant_winrate(
        self, puuid: str, match_count: int = 10
    ) -> Optional[float]:
        """
        Calculate winrate for a participant from their last N matches.

        Checks DB first for efficiency, falls back to API if needed.

        Returns:
            Float between 0.0 and 1.0, or None if no matches found
        """
        # Try DB first
        db_winrate, db_wins = await self._get_db_winrate(puuid, match_count)
        if db_winrate is not None:
            return db_winrate

        # Try API with fallback to partial DB data
        try:
            api_winrate = await self._get_api_winrate(puuid, match_count)
            return (
                api_winrate
                if api_winrate is not None
                else self._calculate_winrate_from_results(db_wins)
            )
        except RiotAPIError as e:
            logger.warning(
                "Failed to calculate participant winrate from API",
                puuid=puuid,
                error=str(e),
            )
            return self._calculate_winrate_from_results(db_wins)

    async def _update_progress(
        self, analysis_id: int, completed: int, total: int
    ) -> None:
        """Update analysis progress and time estimate."""
        # Calculate estimated time remaining
        # ~100 requests per 2 minutes = 50 requests per minute
        requests_remaining = max(0, total - completed)
        minutes_remaining = max(0, requests_remaining // 50)

        await self.db.execute(
            update(MatchmakingAnalysis)
            .where(MatchmakingAnalysis.id == analysis_id)
            .values(
                progress=completed,
                total_requests=total,
                estimated_minutes_remaining=minutes_remaining,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self.db.commit()
