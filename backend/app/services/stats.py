"""
Statistics calculation service for match data analysis.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID
import structlog
from collections import Counter, defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from ..models.matches import Match
from ..models.participants import MatchParticipant
from ..models.players import Player
from ..schemas.matches import MatchStatsResponse

logger = structlog.get_logger(__name__)


class StatsService:
    """Service for calculating various statistics from match data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_player_statistics(
        self,
        puuid: str,
        queue_id: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive player statistics.

        Args:
            puuid: Player PUUID
            queue_id: Filter by queue ID
            start_time: Start timestamp
            end_time: End timestamp
            limit: Maximum number of matches to analyze

        Returns:
            Dictionary with comprehensive statistics
        """
        try:
            # Get participant data for the player
            participants = await self._get_player_participants(
                puuid, queue_id, start_time, end_time, limit
            )

            if not participants:
                return self._get_empty_stats(puuid)

            # Calculate basic statistics
            basic_stats = self._calculate_basic_stats(participants)

            # Calculate champion statistics
            champion_stats = await self._calculate_champion_stats(participants)

            # Calculate position statistics
            position_stats = await self._calculate_position_stats(participants)

            # Calculate performance trends
            performance_trends = await self._calculate_performance_trends(participants)

            # Calculate team performance
            team_performance = await self._calculate_team_performance(participants)

            return {
                'puuid': puuid,
                'basic_stats': basic_stats,
                'champion_stats': champion_stats,
                'position_stats': position_stats,
                'performance_trends': performance_trends,
                'team_performance': team_performance,
                'time_period': {
                    'start_time': start_time,
                    'end_time': end_time,
                    'queue_id': queue_id,
                    'matches_analyzed': len(participants)
                }
            }
        except Exception as e:
            logger.error("Failed to calculate player statistics", puuid=puuid, error=str(e))
            raise

    async def calculate_match_statistics(self, match_id: str) -> Dict[str, Any]:
        """
        Calculate statistics for a specific match.

        Args:
            match_id: Match ID

        Returns:
            Dictionary with match statistics
        """
        try:
            # Get all participants in the match
            participants = await self._get_match_participants(match_id)
            if not participants:
                return {}

            # Team statistics
            team_100 = [p for p in participants if p.team_id == 100]
            team_200 = [p for p in participants if p.team_id == 200]

            team_100_stats = self._calculate_team_match_stats(team_100)
            team_200_stats = self._calculate_team_match_stats(team_200)

            # Individual performances
            individual_stats = []
            for participant in participants:
                individual_stats.append({
                    'puuid': str(participant.puuid),
                    'summoner_name': participant.summoner_name,
                    'champion_name': participant.champion_name,
                    'team_id': participant.team_id,
                    'kills': participant.kills,
                    'deaths': participant.deaths,
                    'assists': participant.assists,
                    'kda': float(participant.kda) if participant.kda else 0.0,
                    'cs': participant.cs,
                    'gold_earned': participant.gold_earned,
                    'vision_score': participant.vision_score,
                    'damage_dealt': participant.total_damage_dealt_to_champions,
                    'damage_taken': participant.total_damage_taken,
                    'win': participant.win
                })

            return {
                'match_id': match_id,
                'team_100': team_100_stats,
                'team_200': team_200_stats,
                'individual_performances': individual_stats,
                'match_duration': self._get_match_duration(match_id),
                'total_kills': sum(p.kills for p in participants),
                'total_gold': sum(p.gold_earned for p in participants),
                'total_damage': sum(p.total_damage_dealt_to_champions for p in participants)
            }
        except Exception as e:
            logger.error("Failed to calculate match statistics", match_id=match_id, error=str(e))
            raise

    async def calculate_encounter_statistics(
        self,
        puuid: str,
        limit: int = 50,
        min_encounters: int = 3
    ) -> Dict[str, Any]:
        """
        Calculate encounter statistics for a player.

        Args:
            puuid: Player PUUID
            limit: Number of recent matches to analyze
            min_encounters: Minimum encounters to include in results

        Returns:
            Dictionary with encounter statistics
        """
        try:
            # Get recent matches for the player
            participants = await self._get_player_participants(puuid, limit=limit)
            if not participants:
                return {'puuid': puuid, 'encounters': {}, 'total_encounters': 0}

            # Collect encounter data
            encounter_data = defaultdict(lambda: {'as_teammate': 0, 'as_opponent': 0, 'matches': []})

            for participant in participants:
                match_participants = await self._get_match_participants(participant.match_id)

                for other_participant in match_participants:
                    if str(other_participant.puuid) == puuid:
                        continue

                    other_puuid = str(other_participant.puuid)
                    is_teammate = other_participant.team_id == participant.team_id

                    encounter_data[other_puuid]['as_teammate' if is_teammate else 'as_opponent'] += 1
                    encounter_data[other_puuid]['matches'].append({
                        'match_id': participant.match_id,
                        'summoner_name': other_participant.summoner_name,
                        'champion_name': other_participant.champion_name,
                        'team_id': other_participant.team_id,
                        'is_teammate': is_teammate,
                        'win': other_participant.win,
                        'kda': float(other_participant.kda) if other_participant.kda else 0.0
                    })

            # Filter and process encounters
            processed_encounters = {}
            for other_puuid, data in encounter_data.items():
                total_encounters = data['as_teammate'] + data['as_opponent']
                if total_encounters >= min_encounters:
                    # Calculate win rates
                    teammate_wins = sum(1 for m in data['matches'] if m['is_teammate'] and m['win'])
                    opponent_wins = sum(1 for m in data['matches'] if not m['is_teammate'] and m['win'])

                    processed_encounters[other_puuid] = {
                        'total_encounters': total_encounters,
                        'as_teammate': data['as_teammate'],
                        'as_opponent': data['as_opponent'],
                        'teammate_win_rate': teammate_wins / data['as_teammate'] if data['as_teammate'] > 0 else 0.0,
                        'opponent_win_rate': opponent_wins / data['as_opponent'] if data['as_opponent'] > 0 else 0.0,
                        'avg_kda': sum(m['kda'] for m in data['matches']) / len(data['matches']),
                        'recent_matches': data['matches'][-5:]  # Last 5 encounters
                    }

            return {
                'puuid': puuid,
                'encounters': processed_encounters,
                'total_unique_encounters': len(processed_encounters),
                'matches_analyzed': len(participants)
            }
        except Exception as e:
            logger.error("Failed to calculate encounter statistics", puuid=puuid, error=str(e))
            raise

    async def _get_player_participants(
        self,
        puuid: str,
        queue_id: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100
    ) -> List[MatchParticipant]:
        """Get participant data for a player."""
        query = select(MatchParticipant).join(Match).where(
            MatchParticipant.puuid == puuid
        ).order_by(desc(Match.game_creation)).limit(limit)

        if queue_id:
            query = query.where(Match.queue_id == queue_id)
        if start_time:
            query = query.where(Match.game_creation >= start_time)
        if end_time:
            query = query.where(Match.game_creation <= end_time)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _get_match_participants(self, match_id: str) -> List[MatchParticipant]:
        """Get all participants in a match."""
        query = select(MatchParticipant).where(MatchParticipant.match_id == match_id)
        result = await self.db.execute(query)
        return result.scalars().all()

    def _calculate_basic_stats(self, participants: List[MatchParticipant]) -> Dict[str, Any]:
        """Calculate basic player statistics."""
        if not participants:
            return self._get_empty_basic_stats()

        total_matches = len(participants)
        wins = sum(1 for p in participants if p.win)
        losses = total_matches - wins

        total_kills = sum(p.kills for p in participants)
        total_deaths = sum(p.deaths for p in participants)
        total_assists = sum(p.assists for p in participants)
        total_cs = sum(p.cs for p in participants)
        total_vision = sum(p.vision_score for p in participants)
        total_gold = sum(p.gold_earned for p in participants)
        total_damage = sum(p.total_damage_dealt_to_champions for p in participants)

        return {
            'total_matches': total_matches,
            'wins': wins,
            'losses': losses,
            'win_rate': wins / total_matches if total_matches > 0 else 0.0,
            'avg_kills': total_kills / total_matches if total_matches > 0 else 0.0,
            'avg_deaths': total_deaths / total_matches if total_matches > 0 else 0.0,
            'avg_assists': total_assists / total_matches if total_matches > 0 else 0.0,
            'avg_kda': self._safe_divide(total_kills + total_assists, total_deaths),
            'avg_cs': total_cs / total_matches if total_matches > 0 else 0.0,
            'avg_vision_score': total_vision / total_matches if total_matches > 0 else 0.0,
            'avg_gold_earned': total_gold / total_matches if total_matches > 0 else 0.0,
            'avg_damage_dealt': total_damage / total_matches if total_matches > 0 else 0.0,
            'max_kills': max(p.kills for p in participants),
            'max_deaths': max(p.deaths for p in participants),
            'max_assists': max(p.assists for p in participants),
            'perfect_games': sum(1 for p in participants if p.deaths == 0),
            'double_kills': sum(getattr(p, 'double_kills', 0) for p in participants),
            'triple_kills': sum(getattr(p, 'triple_kills', 0) for p in participants),
            'quadra_kills': sum(getattr(p, 'quadra_kills', 0) for p in participants),
            'penta_kills': sum(getattr(p, 'penta_kills', 0) for p in participants)
        }

    async def _calculate_champion_stats(self, participants: List[MatchParticipant]) -> Dict[str, Any]:
        """Calculate champion-specific statistics."""
        champion_stats = defaultdict(lambda: {'matches': 0, 'wins': 0, 'kills': 0, 'deaths': 0, 'assists': 0, 'cs': 0})

        for participant in participants:
            champ_name = participant.champion_name
            champion_stats[champ_name]['matches'] += 1
            if participant.win:
                champion_stats[champ_name]['wins'] += 1
            champion_stats[champ_name]['kills'] += participant.kills
            champion_stats[champ_name]['deaths'] += participant.deaths
            champion_stats[champ_name]['assists'] += participant.assists
            champion_stats[champ_name]['cs'] += participant.cs

        # Process champion stats
        processed_stats = {}
        for champ_name, stats in champion_stats.items():
            matches = stats['matches']
            processed_stats[champ_name] = {
                'matches': matches,
                'wins': stats['wins'],
                'win_rate': stats['wins'] / matches if matches > 0 else 0.0,
                'avg_kills': stats['kills'] / matches if matches > 0 else 0.0,
                'avg_deaths': stats['deaths'] / matches if matches > 0 else 0.0,
                'avg_assists': stats['assists'] / matches if matches > 0 else 0.0,
                'avg_kda': self._safe_divide(stats['kills'] + stats['assists'], stats['deaths']),
                'avg_cs': stats['cs'] / matches if matches > 0 else 0.0
            }

        return processed_stats

    async def _calculate_position_stats(self, participants: List[MatchParticipant]) -> Dict[str, Any]:
        """Calculate position-specific statistics."""
        position_stats = defaultdict(lambda: {'matches': 0, 'wins': 0, 'kills': 0, 'deaths': 0, 'assists': 0})

        for participant in participants:
            position = participant.individual_position or 'UNKNOWN'
            position_stats[position]['matches'] += 1
            if participant.win:
                position_stats[position]['wins'] += 1
            position_stats[position]['kills'] += participant.kills
            position_stats[position]['deaths'] += participant.deaths
            position_stats[position]['assists'] += participant.assists

        # Process position stats
        processed_stats = {}
        for position, stats in position_stats.items():
            matches = stats['matches']
            processed_stats[position] = {
                'matches': matches,
                'wins': stats['wins'],
                'win_rate': stats['wins'] / matches if matches > 0 else 0.0,
                'avg_kills': stats['kills'] / matches if matches > 0 else 0.0,
                'avg_deaths': stats['deaths'] / matches if matches > 0 else 0.0,
                'avg_assists': stats['assists'] / matches if matches > 0 else 0.0,
                'avg_kda': self._safe_divide(stats['kills'] + stats['assists'], stats['deaths'])
            }

        return processed_stats

    async def _calculate_performance_trends(self, participants: List[MatchParticipant]) -> Dict[str, Any]:
        """Calculate performance trends over time."""
        if len(participants) < 5:
            return {'recent_form': 'insufficient_data'}

        # Sort by match creation time (most recent first)
        sorted_participants = sorted(participants, key=lambda p: p.match.game_creation, reverse=True)

        # Recent form (last 5 games)
        recent_5 = sorted_participants[:5]
        recent_5_wins = sum(1 for p in recent_5 if p.win)
        recent_5_wr = recent_5_wins / len(recent_5)

        # Last 10 games
        recent_10 = sorted_participants[:10]
        recent_10_wins = sum(1 for p in recent_10 if p.win)
        recent_10_wr = recent_10_wins / len(recent_10)

        # Overall trend
        first_half = sorted_participants[len(sorted_participants)//2:]
        second_half = sorted_participants[:len(sorted_participants)//2]

        first_half_wr = sum(1 for p in first_half if p.win) / len(first_half) if first_half else 0.0
        second_half_wr = sum(1 for p in second_half if p.win) / len(second_half) if second_half else 0.0

        return {
            'recent_form': 'hot' if recent_5_wr >= 0.8 else 'cold' if recent_5_wr <= 0.2 else 'neutral',
            'last_5_games_win_rate': recent_5_wr,
            'last_10_games_win_rate': recent_10_wr,
            'first_half_win_rate': first_half_wr,
            'second_half_win_rate': second_half_wr,
            'improvement_trend': 'improving' if second_half_wr > first_half_wr else 'declining' if second_half_wr < first_half_wr else 'stable'
        }

    async def _calculate_team_performance(self, participants: List[MatchParticipant]) -> Dict[str, Any]:
        """Calculate team performance statistics."""
        team_stats = defaultdict(lambda: {'matches': 0, 'wins': 0, 'kills': 0, 'deaths': 0})

        for participant in participants:
            team_id = participant.team_id
            team_stats[team_id]['matches'] += 1
            if participant.win:
                team_stats[team_id]['wins'] += 1
            team_stats[team_id]['kills'] += participant.kills
            team_stats[team_id]['deaths'] += participant.deaths

        processed_stats = {}
        for team_id, stats in team_stats.items():
            matches = stats['matches']
            processed_stats[f'team_{team_id}'] = {
                'matches': matches,
                'wins': stats['wins'],
                'win_rate': stats['wins'] / matches if matches > 0 else 0.0,
                'avg_kills': stats['kills'] / matches if matches > 0 else 0.0,
                'avg_deaths': stats['deaths'] / matches if matches > 0 else 0.0
            }

        return processed_stats

    def _calculate_team_match_stats(self, team_participants: List[MatchParticipant]) -> Dict[str, Any]:
        """Calculate statistics for a team in a specific match."""
        if not team_participants:
            return {}

        wins = sum(1 for p in team_participants if p.win)
        return {
            'wins': wins,
            'losses': len(team_participants) - wins,
            'win_rate': wins / len(team_participants),
            'total_kills': sum(p.kills for p in team_participants),
            'total_deaths': sum(p.deaths for p in team_participants),
            'total_assists': sum(p.assists for p in team_participants),
            'total_gold': sum(p.gold_earned for p in team_participants),
            'total_damage': sum(p.total_damage_dealt_to_champions for p in team_participants),
            'avg_kda': self._safe_divide(
                sum(p.kills + p.assists for p in team_participants),
                sum(p.deaths for p in team_participants)
            )
        }

    async def _get_match_duration(self, match_id: str) -> Optional[int]:
        """Get match duration in seconds."""
        query = select(Match.game_duration).where(Match.match_id == match_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    def _safe_divide(self, numerator: float, denominator: float) -> float:
        """Safely divide two numbers."""
        if denominator == 0:
            return numerator
        return numerator / denominator

    def _get_empty_stats(self, puuid: str) -> Dict[str, Any]:
        """Get empty statistics structure."""
        return {
            'puuid': puuid,
            'basic_stats': self._get_empty_basic_stats(),
            'champion_stats': {},
            'position_stats': {},
            'performance_trends': {'recent_form': 'no_data'},
            'team_performance': {},
            'time_period': {
                'start_time': None,
                'end_time': None,
                'queue_id': None,
                'matches_analyzed': 0
            }
        }

    def _get_empty_basic_stats(self) -> Dict[str, Any]:
        """Get empty basic statistics structure."""
        return {
            'total_matches': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'avg_kills': 0.0,
            'avg_deaths': 0.0,
            'avg_assists': 0.0,
            'avg_kda': 0.0,
            'avg_cs': 0.0,
            'avg_vision_score': 0.0,
            'avg_gold_earned': 0.0,
            'avg_damage_dealt': 0.0,
            'max_kills': 0,
            'max_deaths': 0,
            'max_assists': 0,
            'perfect_games': 0,
            'double_kills': 0,
            'triple_kills': 0,
            'quadra_kills': 0,
            'penta_kills': 0
        }