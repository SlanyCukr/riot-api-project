"""
Pydantic models for Riot API response data.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


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
    revision_date: Optional[datetime] = Field(None, alias="revisionDate")

    @field_validator('revision_date', mode='before')
    @classmethod
    def parse_timestamp(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v / 1000)
        return v

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
    team_id: int = Field(..., alias="teamId")
    win: bool
    champion_name: str = Field(..., alias="championName")
    kills: int
    deaths: int
    assists: int
    champ_level: int = Field(..., alias="champLevel")
    vision_score: Optional[float] = Field(None, alias="visionScore")
    gold_earned: int = Field(..., alias="goldEarned")
    total_minions_killed: int = Field(..., alias="totalMinionsKilled")
    neutral_minions_killed: int = Field(..., alias="neutralMinionsKilled")
    role: Optional[str] = None
    lane: Optional[str] = None
    individual_position: Optional[str] = Field(None, alias="individualPosition")
    team_position: Optional[str] = Field(None, alias="teamPosition")
    challenges: Optional[Dict[str, Any]] = None
    perks: Optional[Dict[str, Any]] = None

    @property
    def kda(self) -> float:
        """Calculate KDA (kills + assists) / deaths."""
        if self.deaths == 0:
            return self.kills + self.assists
        return (self.kills + self.assists) / self.deaths

    @property
    def cs_per_minute(self) -> float:
        """Calculate CS per minute."""
        if not hasattr(self, '_game_duration') or self._game_duration == 0:
            return 0
        total_cs = self.total_minions_killed + self.neutral_minions_killed
        return (total_cs * 60) / self._game_duration

    model_config = ConfigDict(populate_by_name=True)


class TeamDTO(BaseModel):
    """Match team information."""
    team_id: int = Field(..., alias="teamId")
    win: bool
    bans: Optional[List[Dict[str, Any]]] = None
    objectives: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class MatchInfoDTO(BaseModel):
    """Match information."""
    game_creation: int = Field(..., alias="gameCreation")
    game_duration: int = Field(..., alias="gameDuration")
    game_start_timestamp: Optional[int] = Field(None, alias="gameStartTimestamp")
    queue_id: int = Field(..., alias="queueId")
    map_id: int = Field(..., alias="mapId")
    game_version: str = Field(..., alias="gameVersion")
    game_mode: str = Field(..., alias="gameMode")
    game_type: str = Field(..., alias="gameType")
    participants: List[ParticipantDTO]
    teams: List[TeamDTO]
    platform_id: str = Field(..., alias="platformId")

    @property
    def game_creation_datetime(self) -> datetime:
        """Get game creation as datetime."""
        return datetime.fromtimestamp(self.game_creation / 1000)

    model_config = ConfigDict(populate_by_name=True)


class MatchMetadataDTO(BaseModel):
    """Match metadata."""
    match_id: str = Field(..., alias="matchId")
    data_version: str = Field(..., alias="dataVersion")
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

    @property
    def game_duration_minutes(self) -> float:
        """Get game duration in minutes."""
        return self.info.game_duration / 60

    def get_participant_by_puuid(self, puuid: str) -> Optional[ParticipantDTO]:
        """Get participant by PUUID."""
        for participant in self.info.participants:
            if participant.puuid == puuid:
                return participant
        return None

    def get_participants_by_team(self, team_id: int) -> List[ParticipantDTO]:
        """Get all participants from a specific team."""
        return [p for p in self.info.participants if p.team_id == team_id]

    def get_winning_team(self) -> Optional[TeamDTO]:
        """Get the winning team."""
        for team in self.info.teams:
            if team.win:
                return team
        return None

    model_config = ConfigDict(populate_by_name=True)


class LeagueEntryDTO(BaseModel):
    """League entry information."""
    league_id: str = Field(..., alias="leagueId")
    summoner_id: str = Field(..., alias="summonerId")
    summoner_name: str = Field(..., alias="summonerName")
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

    @property
    def full_rank(self) -> str:
        """Get full rank string (e.g., 'Gold II')."""
        return f"{self.tier.capitalize()} {self.rank}"

    model_config = ConfigDict(populate_by_name=True)


class CurrentGameParticipantDTO(BaseModel):
    """Current game participant information."""
    champion_id: int = Field(..., alias="championId")
    summoner_name: str = Field(..., alias="summonerName")
    summoner_id: str = Field(..., alias="summonerId")
    team_id: int = Field(..., alias="teamId")
    profile_icon_id: int = Field(..., alias="profileIconId")
    summoner_spell1_id: int = Field(..., alias="spell1Id")
    summoner_spell2_id: int = Field(..., alias="spell2Id")
    game_customization_objects: Optional[List[Dict[str, Any]]] = Field(None, alias="gameCustomizationObjects")
    bot: bool = Field(..., alias="bot")
    perks: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class ObserverDTO(BaseModel):
    """Observer information for current game."""
    encryption_key: Optional[str] = Field(None, alias="encryptionKey")

    model_config = ConfigDict(populate_by_name=True)


class CurrentGameInfoDTO(BaseModel):
    """Current game information."""
    game_id: int = Field(..., alias="gameId")
    map_id: int = Field(..., alias="mapId")
    game_mode: str = Field(..., alias="gameMode")
    game_type: str = Field(..., alias="gameType")
    game_queue_config_id: int = Field(..., alias="gameQueueConfigId")
    participants: List[CurrentGameParticipantDTO]
    observers: ObserverDTO
    platform_id: str = Field(..., alias="platformId")
    banned_champions: Optional[List[Dict[str, Any]]] = None
    game_start_time: Optional[int] = Field(None, alias="gameStartTime")
    game_length: Optional[int] = Field(None, alias="gameLength")

    @property
    def game_start_datetime(self) -> Optional[datetime]:
        """Get game start as datetime."""
        if self.game_start_time is None:
            return None
        return datetime.fromtimestamp(self.game_start_time / 1000)

    model_config = ConfigDict(populate_by_name=True)


class FeaturedGameParticipantDTO(BaseModel):
    """Featured game participant information."""
    champion_id: int = Field(..., alias="championId")
    summoner_name: str = Field(..., alias="summonerName")
    team_id: int = Field(..., alias="teamId")

    model_config = ConfigDict(populate_by_name=True)


class FeaturedGameInfoDTO(BaseModel):
    """Featured game information."""
    game_id: int = Field(..., alias="gameId")
    map_id: int = Field(..., alias="mapId")
    game_mode: str = Field(..., alias="gameMode")
    game_type: str = Field(..., alias="gameType")
    game_queue_config_id: int = Field(..., alias="gameQueueConfigId")
    participants: List[FeaturedGameParticipantDTO]
    observers: ObserverDTO
    platform_id: str = Field(..., alias="platformId")
    banned_champions: Optional[List[Dict[str, Any]]] = None
    game_start_time: Optional[int] = Field(None, alias="gameStartTime")
    game_length: Optional[int] = Field(None, alias="gameLength")

    model_config = ConfigDict(populate_by_name=True)


class FeaturedGamesDTO(BaseModel):
    """Featured games response."""
    game_list: List[FeaturedGameInfoDTO] = Field(..., alias="gameList")
    client_refresh_interval: int = Field(..., alias="clientRefreshInterval")

    model_config = ConfigDict(populate_by_name=True)


class ActiveShardDTO(BaseModel):
    """Active shard information."""
    puuid: str
    game: str
    active_shard: str = Field(..., alias="activeShard")

    model_config = ConfigDict(populate_by_name=True)