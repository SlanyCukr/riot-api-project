"""Data transformation utilities for Riot API match data."""

from typing import Dict, List, Any
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
            info = match_data.get("info", {})
            metadata = match_data.get("metadata", {})

            # Transform match
            match_dict = self._transform_match_info(metadata, info)

            # Transform participants
            participants = self._transform_participants(
                metadata.get("matchId"), info.get("participants", [])
            )

            return {"match": match_dict, "participants": participants}
        except Exception as e:
            logger.error(
                "Failed to transform match data",
                error=str(e),
                match_id=match_data.get("metadata", {}).get("matchId"),
            )
            raise

    def _transform_match_info(
        self, metadata: Dict[str, Any], info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform match information."""
        return {
            "match_id": metadata.get("matchId"),
            "platform_id": info.get("platformId"),
            "game_creation": info.get("gameCreation"),
            "game_duration": info.get("gameDuration"),
            "queue_id": info.get("queueId"),
            "game_version": info.get("gameVersion"),
            "map_id": info.get("mapId"),
            "game_mode": info.get("gameMode"),
            "game_type": info.get("gameType"),
            "game_end_timestamp": info.get("gameEndTimestamp"),
            "tournament_id": info.get("tournamentId"),
        }

    def _transform_participants(
        self, match_id: str, participants: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Transform participant data."""
        transformed_participants: List[Dict[str, Any]] = []

        for participant in participants:
            try:
                participant_dict: Dict[str, Any] = {
                    "match_id": match_id,
                    "puuid": participant.get("puuid"),
                    "summoner_name": participant.get("summonerName"),
                    "team_id": participant.get("teamId"),
                    "champion_id": participant.get("championId"),
                    "champion_name": participant.get("championName"),
                    "kills": participant.get("kills", 0),
                    "deaths": participant.get("deaths", 0),
                    "assists": participant.get("assists", 0),
                    "win": participant.get("win", False),
                    "gold_earned": participant.get("goldEarned", 0),
                    "vision_score": participant.get("visionScore", 0),
                    "cs": self._calculate_cs(participant),
                    "kda": self._calculate_participant_kda(participant),
                    "champ_level": participant.get("champLevel", 1),
                    "total_damage_dealt": participant.get("totalDamageDealt", 0),
                    "total_damage_dealt_to_champions": participant.get(
                        "totalDamageDealtToChampions", 0
                    ),
                    "total_damage_taken": participant.get("damageTaken", 0),
                    "total_heal": participant.get("totalHeal", 0),
                    "individual_position": participant.get("individualPosition"),
                    "team_position": participant.get("teamPosition"),
                    "role": participant.get("role"),
                }
                transformed_participants.append(participant_dict)
            except Exception as e:
                logger.warning(
                    "Failed to transform participant",
                    match_id=match_id,
                    summoner_name=participant.get("summonerName"),
                    error=str(e),
                )
                continue

        return transformed_participants

    def _calculate_cs(self, participant: Dict[str, Any]) -> int:
        """Calculate total creep score."""
        return participant.get("totalMinionsKilled", 0) + participant.get(
            "neutralMinionsKilled", 0
        )

    def _calculate_participant_kda(self, participant: Dict[str, Any]) -> float:
        """Calculate KDA for a participant."""
        kills = participant.get("kills", 0)
        deaths = participant.get("deaths", 0)
        assists = participant.get("assists", 0)

        if deaths == 0:
            return float(kills + assists)
        return (kills + assists) / deaths

    def validate_match_data(self, match_data: Dict[str, Any]) -> bool:
        """
        Validate that match data has required fields.

        Args:
            match_data: Raw match data from Riot API

        Returns:
            True if valid, False otherwise
        """
        from ..utils.validation import validate_nested_fields, validate_list_items

        required_structure = {
            "metadata": ["matchId"],
            "info": [
                "gameCreation",
                "gameDuration",
                "queueId",
                "gameVersion",
                "mapId",
                "participants",
            ],
        }

        required_participant_fields = [
            "puuid",
            "summonerName",
            "teamId",
            "championId",
            "championName",
        ]

        try:
            # Validate nested structure
            if not validate_nested_fields(match_data, required_structure):
                return False

            # Validate participants list
            participants = match_data.get("info", {}).get("participants", [])
            if not validate_list_items(
                participants, required_participant_fields, "participant"
            ):
                return False

            return True
        except Exception as e:
            logger.error("Error validating match data", error=str(e))
            return False
