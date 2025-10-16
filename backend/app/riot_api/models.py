"""Pydantic models for Riot API response data."""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class AccountDTO(BaseModel):
    """Riot Account information."""

    puuid: str
    game_name: str = Field(..., alias="gameName")
    tag_line: str = Field(..., alias="tagLine")

    model_config = ConfigDict(populate_by_name=True)


class SummonerDTO(BaseModel):
    """League of Legends Summoner information."""

    id: Optional[str] = None
    puuid: str
    name: Optional[str] = None
    profile_icon_id: int = Field(..., alias="profileIconId")
    summoner_level: int = Field(..., alias="summonerLevel")

    model_config = ConfigDict(populate_by_name=True)


class MatchListDTO(BaseModel):
    """Match list response."""

    match_ids: List[str] = Field(..., alias="matchIds")
    start: int
    count: int
    total: Optional[int] = None
    puuid: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class ParticipantDTO(BaseModel):
    """Match participant information."""

    puuid: str
    summoner_name: str = Field(..., alias="summonerName")
    summoner_id: Optional[str] = Field(None, alias="summonerId")
    summoner_level: int = Field(..., alias="summonerLevel")

    # Riot ID fields (newer API format)
    riot_id_game_name: Optional[str] = Field(None, alias="riotIdGameName")
    riot_id_tagline: Optional[str] = Field(None, alias="riotIdTagline")

    team_id: int = Field(..., alias="teamId")
    win: bool
    champion_id: int = Field(..., alias="championId")
    champion_name: str = Field(..., alias="championName")
    kills: int
    deaths: int
    assists: int
    champ_level: int = Field(..., alias="champLevel")
    vision_score: Optional[float] = Field(None, alias="visionScore")
    gold_earned: int = Field(..., alias="goldEarned")
    total_minions_killed: int = Field(..., alias="totalMinionsKilled")
    neutral_minions_killed: int = Field(..., alias="neutralMinionsKilled")

    # Damage stats
    total_damage_dealt_to_champions: int = Field(
        ..., alias="totalDamageDealtToChampions"
    )
    total_damage_taken: int = Field(..., alias="totalDamageTaken")
    role: Optional[str] = None
    individual_position: Optional[str] = Field(None, alias="individualPosition")
    team_position: Optional[str] = Field(None, alias="teamPosition")

    @property
    def kda(self) -> float:
        """Calculate KDA (kills + assists) / deaths."""
        if self.deaths == 0:
            return self.kills + self.assists
        return (self.kills + self.assists) / self.deaths

    model_config = ConfigDict(populate_by_name=True)


class MatchInfoDTO(BaseModel):
    """Match information."""

    game_creation: int = Field(..., alias="gameCreation")
    game_duration: int = Field(..., alias="gameDuration")
    queue_id: int = Field(..., alias="queueId")
    map_id: int = Field(..., alias="mapId")
    game_version: str = Field(..., alias="gameVersion")
    game_mode: str = Field(..., alias="gameMode")
    game_type: str = Field(..., alias="gameType")
    participants: List[ParticipantDTO]
    platform_id: str = Field(..., alias="platformId")

    model_config = ConfigDict(populate_by_name=True)


class MatchMetadataDTO(BaseModel):
    """Match metadata."""

    match_id: str = Field(..., alias="matchId")
    participants: List[str]

    model_config = ConfigDict(populate_by_name=True)


class MatchDTO(BaseModel):
    """Complete match data."""

    metadata: MatchMetadataDTO
    info: MatchInfoDTO

    @property
    def match_id(self) -> str:
        """Get match ID from metadata."""
        return self.metadata.match_id

    model_config = ConfigDict(populate_by_name=True)


class LeagueEntryDTO(BaseModel):
    """League entry information."""

    league_id: str = Field(..., alias="leagueId")
    summoner_id: Optional[str] = Field(
        None, alias="summonerId"
    )  # Optional when using by-puuid endpoint
    summoner_name: Optional[str] = Field(
        None, alias="summonerName"
    )  # Optional when using by-puuid endpoint
    puuid: Optional[str] = None  # Available when using by-puuid endpoint
    queue_type: str = Field(..., alias="queueType")
    tier: str
    rank: str
    league_points: int = Field(..., alias="leaguePoints")
    wins: int
    losses: int
    veteran: bool = Field(..., alias="veteran")
    inactive: bool = Field(..., alias="inactive")
    fresh_blood: bool = Field(..., alias="freshBlood")
    hot_streak: bool = Field(..., alias="hotStreak")

    @property
    def win_rate(self) -> float:
        """Calculate win rate."""
        total_games = self.wins + self.losses
        if total_games == 0:
            return 0
        return (self.wins / total_games) * 100

    model_config = ConfigDict(populate_by_name=True)
