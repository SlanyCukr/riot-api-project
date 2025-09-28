"""
Data transformation utilities for Riot API match data.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class MatchTransformer:
    """Transform Riot API match data to database format."""

    def transform_match_data(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Riot API match data to database format.

        Args:
            match_data: Raw match data from Riot API

        Returns:
            Transformed data ready for database insertion
        """
        try:
            info = match_data.get('info', {})
            metadata = match_data.get('metadata', {})

            # Transform match
            match_dict = self._transform_match_info(metadata, info)

            # Transform participants
            participants = self._transform_participants(metadata.get('matchId'), info.get('participants', []))

            return {
                'match': match_dict,
                'participants': participants
            }
        except Exception as e:
            logger.error("Failed to transform match data", error=str(e), match_id=match_data.get('metadata', {}).get('matchId'))
            raise

    def _transform_match_info(self, metadata: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
        """Transform match information."""
        return {
            'match_id': metadata.get('matchId'),
            'platform_id': info.get('platformId'),
            'game_creation': info.get('gameCreation'),
            'game_duration': info.get('gameDuration'),
            'queue_id': info.get('queueId'),
            'game_version': info.get('gameVersion'),
            'map_id': info.get('mapId'),
            'game_mode': info.get('gameMode'),
            'game_type': info.get('gameType'),
            'game_end_timestamp': info.get('gameEndTimestamp'),
            'tournament_id': info.get('tournamentId')
        }

    def _transform_participants(self, match_id: str, participants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform participant data."""
        transformed_participants = []

        for participant in participants:
            try:
                participant_dict = {
                    'match_id': match_id,
                    'puuid': participant.get('puuid'),
                    'summoner_name': participant.get('summonerName'),
                    'team_id': participant.get('teamId'),
                    'champion_id': participant.get('championId'),
                    'champion_name': participant.get('championName'),
                    'kills': participant.get('kills', 0),
                    'deaths': participant.get('deaths', 0),
                    'assists': participant.get('assists', 0),
                    'win': participant.get('win', False),
                    'gold_earned': participant.get('goldEarned', 0),
                    'vision_score': participant.get('visionScore', 0),
                    'cs': self._calculate_cs(participant),
                    'kda': self._calculate_participant_kda(participant),
                    'champ_level': participant.get('champLevel', 1),
                    'total_damage_dealt': participant.get('totalDamageDealt', 0),
                    'total_damage_dealt_to_champions': participant.get('totalDamageDealtToChampions', 0),
                    'total_damage_taken': participant.get('damageTaken', 0),
                    'total_heal': participant.get('totalHeal', 0),
                    'individual_position': participant.get('individualPosition'),
                    'team_position': participant.get('teamPosition'),
                    'role': participant.get('role')
                }
                transformed_participants.append(participant_dict)
            except Exception as e:
                logger.warning("Failed to transform participant",
                             match_id=match_id,
                             summoner_name=participant.get('summonerName'),
                             error=str(e))
                continue

        return transformed_participants

    def _calculate_cs(self, participant: Dict[str, Any]) -> int:
        """Calculate total creep score."""
        return (
            participant.get('totalMinionsKilled', 0) +
            participant.get('neutralMinionsKilled', 0)
        )

    def _calculate_participant_kda(self, participant: Dict[str, Any]) -> float:
        """Calculate KDA for a participant."""
        kills = participant.get('kills', 0)
        deaths = participant.get('deaths', 0)
        assists = participant.get('assists', 0)

        if deaths == 0:
            return float(kills + assists)
        return (kills + assists) / deaths

    def extract_encounters_from_match(self, match_data: Dict[str, Any], target_puuid: str) -> Dict[str, Any]:
        """
        Extract encounter information from a match for a specific player.

        Args:
            match_data: Raw match data from Riot API
            target_puuid: PUUID of the player to find encounters for

        Returns:
            Dictionary with encounter information
        """
        try:
            info = match_data.get('info', {})
            metadata = match_data.get('metadata', {})
            participants = info.get('participants', [])

            # Find the target participant
            target_participant = None
            for participant in participants:
                if participant.get('puuid') == target_puuid:
                    target_participant = participant
                    break

            if not target_participant:
                return {'match_id': metadata.get('matchId'), 'encounters': []}

            encounters = []
            for participant in participants:
                if participant.get('puuid') == target_puuid:
                    continue

                # Determine relationship (teammate or opponent)
                is_teammate = participant.get('teamId') == target_participant.get('teamId')

                encounter = {
                    'puuid': participant.get('puuid'),
                    'summoner_name': participant.get('summonerName'),
                    'champion_name': participant.get('championName'),
                    'team_id': participant.get('teamId'),
                    'is_teammate': is_teammate,
                    'win': participant.get('win', False),
                    'kills': participant.get('kills', 0),
                    'deaths': participant.get('deaths', 0),
                    'assists': participant.get('assists', 0),
                    'kda': self._calculate_participant_kda(participant)
                }
                encounters.append(encounter)

            return {
                'match_id': metadata.get('matchId'),
                'game_creation': info.get('gameCreation'),
                'target_win': target_participant.get('win', False),
                'encounters': encounters
            }
        except Exception as e:
            logger.error("Failed to extract encounters from match",
                        match_id=match_data.get('metadata', {}).get('matchId'),
                        target_puuid=target_puuid,
                        error=str(e))
            raise

    def validate_match_data(self, match_data: Dict[str, Any]) -> bool:
        """
        Validate that match data has required fields.

        Args:
            match_data: Raw match data from Riot API

        Returns:
            True if valid, False otherwise
        """
        required_fields = {
            'metadata': ['matchId'],
            'info': ['gameCreation', 'gameDuration', 'queueId', 'gameVersion', 'mapId', 'participants']
        }

        try:
            # Check metadata
            metadata = match_data.get('metadata', {})
            for field in required_fields['metadata']:
                if field not in metadata:
                    logger.warning("Missing required metadata field", field=field)
                    return False

            # Check info
            info = match_data.get('info', {})
            for field in required_fields['info']:
                if field not in info:
                    logger.warning("Missing required info field", field=field)
                    return False

            # Check participants
            participants = info.get('participants', [])
            if not participants:
                logger.warning("No participants found in match")
                return False

            # Check each participant has required fields
            required_participant_fields = ['puuid', 'summonerName', 'teamId', 'championId', 'championName']
            for i, participant in enumerate(participants):
                for field in required_participant_fields:
                    if field not in participant:
                        logger.warning("Missing required participant field",
                                     participant_index=i, field=field)
                        return False

            return True
        except Exception as e:
            logger.error("Error validating match data", error=str(e))
            return False

    def filter_participant_fields(self, participant: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
        """
        Filter participant data to include only specified fields.

        Args:
            participant: Full participant data
            fields: List of fields to include

        Returns:
            Filtered participant data
        """
        return {field: participant.get(field) for field in fields}

    def aggregate_match_statistics(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate statistics from multiple matches.

        Args:
            matches: List of match data

        Returns:
            Aggregated statistics
        """
        try:
            total_matches = len(matches)
            if total_matches == 0:
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
                    'avg_vision_score': 0.0
                }

            total_kills = 0
            total_deaths = 0
            total_assists = 0
            total_cs = 0
            total_vision = 0
            wins = 0

            for match in matches:
                # This would need to be called with specific participant data
                # For now, we'll return a placeholder
                pass

            # Calculate averages
            avg_kda = (total_kills + total_assists) / total_deaths if total_deaths > 0 else total_kills + total_assists

            return {
                'total_matches': total_matches,
                'wins': wins,
                'losses': total_matches - wins,
                'win_rate': wins / total_matches if total_matches > 0 else 0.0,
                'avg_kills': total_kills / total_matches if total_matches > 0 else 0.0,
                'avg_deaths': total_deaths / total_matches if total_matches > 0 else 0.0,
                'avg_assists': total_assists / total_matches if total_matches > 0 else 0.0,
                'avg_kda': avg_kda,
                'avg_cs': total_cs / total_matches if total_matches > 0 else 0.0,
                'avg_vision_score': total_vision / total_matches if total_matches > 0 else 0.0
            }
        except Exception as e:
            logger.error("Failed to aggregate match statistics", error=str(e))
            raise