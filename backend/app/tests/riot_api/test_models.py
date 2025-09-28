"""
Tests for data models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from backend.app.riot_api.models import (
    AccountDTO,
    SummonerDTO,
    MatchListDTO,
    MatchDTO,
    ParticipantDTO,
    TeamDTO,
    MatchInfoDTO,
    MatchMetadataDTO,
    LeagueEntryDTO,
    CurrentGameInfoDTO,
    FeaturedGamesDTO,
    ActiveShardDTO
)


class TestAccountDTO:
    """Test cases for AccountDTO."""

    def test_valid_account(self):
        """Test creating valid account."""
        account = AccountDTO(
            puuid="test-puuid-123",
            gameName="TestPlayer",
            tagLine="EUW"
        )

        assert account.puuid == "test-puuid-123"
        assert account.game_name == "TestPlayer"
        assert account.tag_line == "EUW"

    def test_account_field_alias(self):
        """Test field alias works correctly."""
        data = {
            "puuid": "test-puuid-123",
            "gameName": "TestPlayer",
            "tagLine": "EUW"
        }

        account = AccountDTO(**data)
        assert account.game_name == "TestPlayer"
        assert account.tag_line == "EUW"


class TestSummonerDTO:
    """Test cases for SummonerDTO."""

    def test_valid_summoner(self):
        """Test creating valid summoner."""
        summoner = SummonerDTO(
            id="test-summoner-id",
            puuid="test-puuid-123",
            name="TestPlayer",
            profileIconId=1234,
            summonerLevel=100,
            revisionDate=1234567890000
        )

        assert summoner.id == "test-summoner-id"
        assert summoner.puuid == "test-puuid-123"
        assert summoner.name == "TestPlayer"
        assert summoner.profile_icon_id == 1234
        assert summoner.summoner_level == 100
        assert summoner.revision_date is not None

    def test_summoner_timestamp_parsing(self):
        """Test timestamp parsing for revision date."""
        timestamp_ms = 1234567890000  # Milliseconds since epoch
        expected_dt = datetime.fromtimestamp(timestamp_ms / 1000)

        summoner = SummonerDTO(
            id="test-summoner-id",
            puuid="test-puuid-123",
            name="TestPlayer",
            profileIconId=1234,
            summonerLevel=100,
            revisionDate=timestamp_ms
        )

        assert summoner.revision_date == expected_dt

    def test_summoner_optional_revision_date(self):
        """Test summoner with optional revision date."""
        summoner = SummonerDTO(
            id="test-summoner-id",
            puuid="test-puuid-123",
            name="TestPlayer",
            profileIconId=1234,
            summonerLevel=100,
            revisionDate=None
        )

        assert summoner.revision_date is None

    def test_summoner_field_alias(self):
        """Test field alias works correctly."""
        data = {
            "id": "test-summoner-id",
            "puuid": "test-puuid-123",
            "name": "TestPlayer",
            "profileIconId": 1234,
            "summonerLevel": 100
        }

        summoner = SummonerDTO(**data)
        assert summoner.profile_icon_id == 1234
        assert summoner.summoner_level == 100


class TestMatchListDTO:
    """Test cases for MatchListDTO."""

    def test_valid_match_list(self):
        """Test creating valid match list."""
        match_ids = ["EUW1_123", "EUW1_456", "EUW1_789"]

        match_list = MatchListDTO(
            matchIds=match_ids,
            start=0,
            count=3,
            total=100,
            puuid="test-puuid"
        )

        assert match_list.match_ids == match_ids
        assert match_list.start == 0
        assert match_list.count == 3
        assert match_list.total == 100
        assert match_list.puuid == "test-puuid"

    def test_match_list_field_alias(self):
        """Test field alias works correctly."""
        data = {
            "matchIds": ["EUW1_123"],
            "start": 0,
            "count": 1
        }

        match_list = MatchListDTO(**data)
        assert match_list.match_ids == ["EUW1_123"]
        assert match_list.start == 0
        assert match_list.count == 1


class TestParticipantDTO:
    """Test cases for ParticipantDTO."""

    def test_valid_participant(self):
        """Test creating valid participant."""
        participant = ParticipantDTO(
            puuid="test-puuid",
            summonerName="TestPlayer",
            summonerId="summoner-123",
            teamId=100,
            win=True,
            championName="Zed",
            kills=12,
            deaths=2,
            assists=6,
            champLevel=18,
            visionScore=25.5,
            goldEarned=15000,
            totalMinionsKilled=200,
            neutralMinionsKilled=50,
            role="MIDDLE",
            lane="MID",
            individualPosition="MIDDLE",
            teamPosition="MIDDLE",
            challenges={"kda": 9.0},
            perks={"styles": []}
        )

        assert participant.puuid == "test-puuid"
        assert participant.summoner_name == "TestPlayer"
        assert participant.kills == 12
        assert participant.deaths == 2
        assert participant.assists == 6

    def test_participant_kda_calculation(self):
        """Test KDA calculation."""
        # Test with deaths
        participant1 = ParticipantDTO(
            puuid="test", summonerName="test", teamId=100, win=True,
            championName="Zed", kills=10, deaths=2, assists=5, champLevel=18,
            goldEarned=1000, totalMinionsKilled=100, neutralMinionsKilled=0
        )
        assert participant1.kda == 7.5  # (10 + 5) / 2

        # Test without deaths
        participant2 = ParticipantDTO(
            puuid="test", summonerName="test", teamId=100, win=True,
            championName="Zed", kills=10, deaths=0, assists=5, champLevel=18,
            goldEarned=1000, totalMinionsKilled=100, neutralMinionsKilled=0
        )
        assert participant2.kda == 15  # 10 + 5

    def test_participant_field_alias(self):
        """Test field alias works correctly."""
        data = {
            "puuid": "test-puuid",
            "summonerName": "TestPlayer",
            "teamId": 100,
            "win": True,
            "championName": "Zed",
            "kills": 12,
            "deaths": 2,
            "assists": 6,
            "champLevel": 18,
            "goldEarned": 15000,
            "totalMinionsKilled": 200,
            "neutralMinionsKilled": 50
        }

        participant = ParticipantDTO(**data)
        assert participant.summoner_name == "TestPlayer"
        assert participant.team_id == 100
        assert participant.champion_name == "Zed"
        assert participant.champ_level == 18


class TestTeamDTO:
    """Test cases for TeamDTO."""

    def test_valid_team(self):
        """Test creating valid team."""
        team = TeamDTO(
            teamId=100,
            win=True,
            bans=[{"championId": 1, "pickTurn": 1}],
            objectives={"baron": {"first": True, "kills": 1}}
        )

        assert team.team_id == 100
        assert team.win is True
        assert team.bans is not None
        assert team.objectives is not None

    def test_team_field_alias(self):
        """Test field alias works correctly."""
        data = {
            "teamId": 100,
            "win": True
        }

        team = TeamDTO(**data)
        assert team.team_id == 100
        assert team.win is True


class TestMatchMetadataDTO:
    """Test cases for MatchMetadataDTO."""

    def test_valid_match_metadata(self):
        """Test creating valid match metadata."""
        metadata = MatchMetadataDTO(
            matchId="EUW1_1234567890",
            dataVersion="14.20.555.5555",
            participants=["puuid1", "puuid2", "puuid3"]
        )

        assert metadata.match_id == "EUW1_1234567890"
        assert metadata.data_version == "14.20.555.5555"
        assert metadata.participants == ["puuid1", "puuid2", "puuid3"]

    def test_match_metadata_field_alias(self):
        """Test field alias works correctly."""
        data = {
            "matchId": "EUW1_123",
            "dataVersion": "14.20",
            "participants": ["puuid1"]
        }

        metadata = MatchMetadataDTO(**data)
        assert metadata.match_id == "EUW1_123"
        assert metadata.data_version == "14.20"


class TestMatchInfoDTO:
    """Test cases for MatchInfoDTO."""

    def test_valid_match_info(self):
        """Test creating valid match info."""
        participant = ParticipantDTO(
            puuid="test-puuid", summonerName="TestPlayer", teamId=100, win=True,
            championName="Zed", kills=5, deaths=3, assists=7, champLevel=15,
            goldEarned=10000, totalMinionsKilled=150, neutralMinionsKilled=30
        )

        team = TeamDTO(teamId=100, win=True)

        match_info = MatchInfoDTO(
            gameCreation=1710000000000,
            gameDuration=1800,
            gameStartTimestamp=1710000000000,
            queueId=420,
            mapId=11,
            gameVersion="14.20.555.5555",
            gameMode="CLASSIC",
            gameType="MATCHED_GAME",
            participants=[participant],
            teams=[team],
            platformId="EUW1"
        )

        assert match_info.queue_id == 420
        assert match_info.game_duration == 1800
        assert len(match_info.participants) == 1
        assert len(match_info.teams) == 1

    def test_match_info_field_alias(self):
        """Test field alias works correctly."""
        data = {
            "gameCreation": 1710000000000,
            "gameDuration": 1800,
            "queueId": 420,
            "mapId": 11,
            "gameVersion": "14.20",
            "gameMode": "CLASSIC",
            "gameType": "MATCHED_GAME",
            "participants": [],
            "teams": [],
            "platformId": "EUW1"
        }

        match_info = MatchInfoDTO(**data)
        assert match_info.game_creation == 1710000000000
        assert match_info.game_duration == 1800
        assert match_info.queue_id == 420

    def test_game_creation_datetime(self):
        """Test game creation datetime conversion."""
        timestamp_ms = 1710000000000
        expected_dt = datetime.fromtimestamp(timestamp_ms / 1000)

        data = {
            "gameCreation": timestamp_ms,
            "gameDuration": 1800,
            "queueId": 420,
            "mapId": 11,
            "gameVersion": "14.20",
            "gameMode": "CLASSIC",
            "gameType": "MATCHED_GAME",
            "participants": [],
            "teams": [],
            "platformId": "EUW1"
        }

        match_info = MatchInfoDTO(**data)
        assert match_info.game_creation_datetime == expected_dt


class TestMatchDTO:
    """Test cases for MatchDTO."""

    def test_valid_match(self):
        """Test creating valid match."""
        metadata = MatchMetadataDTO(
            matchId="EUW1_1234567890",
            dataVersion="14.20.555.5555",
            participants=["puuid1", "puuid2"]
        )

        participant = ParticipantDTO(
            puuid="puuid1", summonerName="Player1", teamId=100, win=True,
            championName="Zed", kills=5, deaths=3, assists=7, champLevel=15,
            goldEarned=10000, totalMinionsKilled=150, neutralMinionsKilled=30
        )

        team = TeamDTO(teamId=100, win=True)

        info = MatchInfoDTO(
            gameCreation=1710000000000,
            gameDuration=1800,
            queueId=420,
            mapId=11,
            gameVersion="14.20.555.5555",
            gameMode="CLASSIC",
            gameType="MATCHED_GAME",
            participants=[participant],
            teams=[team],
            platformId="EUW1"
        )

        match = MatchDTO(metadata=metadata, info=info)

        assert match.match_id == "EUW1_1234567890"
        assert match.info.queue_id == 420
        assert match.game_duration_minutes == 30.0  # 1800 seconds / 60

    def test_get_participant_by_puuid(self):
        """Test getting participant by PUUID."""
        participant1 = ParticipantDTO(
            puuid="puuid1", summonerName="Player1", teamId=100, win=True,
            championName="Zed", kills=5, deaths=3, assists=7, champLevel=15,
            goldEarned=10000, totalMinionsKilled=150, neutralMinionsKilled=30
        )

        participant2 = ParticipantDTO(
            puuid="puuid2", summonerName="Player2", teamId=200, win=False,
            championName="Yasuo", kills=3, deaths=5, assists=2, champLevel=14,
            goldEarned=8000, totalMinionsKilled=120, neutralMinionsKilled=25
        )

        match = MatchDTO(
            metadata=MatchMetadataDTO(
                matchId="EUW1_123", dataVersion="14.20", participants=["puuid1", "puuid2"]
            ),
            info=MatchInfoDTO(
                gameCreation=1710000000000, gameDuration=1800, queueId=420, mapId=11,
                gameVersion="14.20", gameMode="CLASSIC", gameType="MATCHED_GAME",
                participants=[participant1, participant2], teams=[],
                platformId="EUW1"
            )
        )

        found = match.get_participant_by_puuid("puuid1")
        assert found is not None
        assert found.puuid == "puuid1"
        assert found.summoner_name == "Player1"

        not_found = match.get_participant_by_puuid("nonexistent")
        assert not_found is None

    def test_get_participants_by_team(self):
        """Test getting participants by team."""
        participant1 = ParticipantDTO(
            puuid="puuid1", summonerName="Player1", teamId=100, win=True,
            championName="Zed", kills=5, deaths=3, assists=7, champLevel=15,
            goldEarned=10000, totalMinionsKilled=150, neutralMinionsKilled=30
        )

        participant2 = ParticipantDTO(
            puuid="puuid2", summonerName="Player2", teamId=200, win=False,
            championName="Yasuo", kills=3, deaths=5, assists=2, champLevel=14,
            goldEarned=8000, totalMinionsKilled=120, neutralMinionsKilled=25
        )

        match = MatchDTO(
            metadata=MatchMetadataDTO(
                matchId="EUW1_123", dataVersion="14.20", participants=["puuid1", "puuid2"]
            ),
            info=MatchInfoDTO(
                gameCreation=1710000000000, gameDuration=1800, queueId=420, mapId=11,
                gameVersion="14.20", gameMode="CLASSIC", gameType="MATCHED_GAME",
                participants=[participant1, participant2], teams=[],
                platformId="EUW1"
            )
        )

        team100 = match.get_participants_by_team(100)
        assert len(team100) == 1
        assert team100[0].puuid == "puuid1"

        team200 = match.get_participants_by_team(200)
        assert len(team200) == 1
        assert team200[0].puuid == "puuid2"

    def test_get_winning_team(self):
        """Test getting winning team."""
        team1 = TeamDTO(teamId=100, win=True)
        team2 = TeamDTO(teamId=200, win=False)

        match = MatchDTO(
            metadata=MatchMetadataDTO(
                matchId="EUW1_123", dataVersion="14.20", participants=[]
            ),
            info=MatchInfoDTO(
                gameCreation=1710000000000, gameDuration=1800, queueId=420, mapId=11,
                gameVersion="14.20", gameMode="CLASSIC", gameType="MATCHED_GAME",
                participants=[], teams=[team1, team2], platformId="EUW1"
            )
        )

        winner = match.get_winning_team()
        assert winner is not None
        assert winner.team_id == 100
        assert winner.win is True


class TestLeagueEntryDTO:
    """Test cases for LeagueEntryDTO."""

    def test_valid_league_entry(self):
        """Test creating valid league entry."""
        entry = LeagueEntryDTO(
            leagueId="test-league",
            summonerId="summoner-123",
            summonerName="TestPlayer",
            queueType="RANKED_SOLO_5x5",
            tier="GOLD",
            rank="II",
            leaguePoints=50,
            wins=25,
            losses=15,
            veteran=False,
            inactive=False,
            freshBlood=False,
            hotStreak=False
        )

        assert entry.league_id == "test-league"
        assert entry.summoner_name == "TestPlayer"
        assert entry.queue_type == "RANKED_SOLO_5x5"
        assert entry.tier == "GOLD"
        assert entry.rank == "II"
        assert entry.league_points == 50

    def test_league_entry_win_rate(self):
        """Test win rate calculation."""
        entry = LeagueEntryDTO(
            leagueId="test", summonerId="test", summonerName="test",
            queueType="RANKED_SOLO_5x5", tier="GOLD", rank="II",
            leaguePoints=50, wins=25, losses=15, veteran=False,
            inactive=False, freshBlood=False, hotStreak=False
        )

        # 25 wins out of 40 total games = 62.5%
        assert entry.win_rate == 62.5

    def test_league_entry_full_rank(self):
        """Test full rank string."""
        entry = LeagueEntryDTO(
            leagueId="test", summonerId="test", summonerName="test",
            queueType="RANKED_SOLO_5x5", tier="GOLD", rank="II",
            leaguePoints=50, wins=25, losses=15, veteran=False,
            inactive=False, freshBlood=False, hotStreak=False
        )

        assert entry.full_rank == "Gold II"

    def test_league_entry_field_alias(self):
        """Test field alias works correctly."""
        data = {
            "leagueId": "test-league",
            "summonerId": "summoner-123",
            "summonerName": "TestPlayer",
            "queueType": "RANKED_SOLO_5x5",
            "tier": "GOLD",
            "rank": "II",
            "leaguePoints": 50,
            "wins": 25,
            "losses": 15,
            "veteran": False,
            "inactive": False,
            "freshBlood": False,
            "hotStreak": False
        }

        entry = LeagueEntryDTO(**data)
        assert entry.league_id == "test-league"
        assert entry.summoner_id == "summoner-123"
        assert entry.summoner_name == "TestPlayer"
        assert entry.league_points == 50
        assert entry.hot_streak is False


class TestCurrentGameInfoDTO:
    """Test cases for CurrentGameInfoDTO."""

    def test_valid_current_game(self):
        """Test creating valid current game info."""
        from backend.app.riot_api.models import CurrentGameParticipantDTO, ObserverDTO

        participant = CurrentGameParticipantDTO(
            championId=238,
            summonerName="TestPlayer",
            summonerId="summoner-123",
            teamId=100,
            profileIconId=1234,
            spell1Id=4,
            spell2Id=14,
            bot=False
        )

        observer = ObserverDTO(encryptionKey="test-key")

        game = CurrentGameInfoDTO(
            gameId=123456789,
            mapId=11,
            gameMode="CLASSIC",
            gameType="MATCHED_GAME",
            gameQueueConfigId=420,
            participants=[participant],
            observers=observer,
            platformId="EUW1",
            gameStartTime=1710000000000,
            gameLength=300
        )

        assert game.game_id == 123456789
        assert game.map_id == 11
        assert len(game.participants) == 1
        assert game.game_start_datetime is not None

    def test_current_game_field_alias(self):
        """Test field alias works correctly."""
        data = {
            "gameId": 123456789,
            "mapId": 11,
            "gameMode": "CLASSIC",
            "gameType": "MATCHED_GAME",
            "gameQueueConfigId": 420,
            "participants": [],
            "observers": {"encryptionKey": "test"},
            "platformId": "EUW1"
        }

        game = CurrentGameInfoDTO(**data)
        assert game.game_id == 123456789
        assert game.map_id == 11
        assert game.game_queue_config_id == 420


class TestFeaturedGamesDTO:
    """Test cases for FeaturedGamesDTO."""

    def test_valid_featured_games(self):
        """Test creating valid featured games."""
        from backend.app.riot_api.models import FeaturedGameInfoDTO

        game = FeaturedGameInfoDTO(
            gameId=123456789,
            mapId=11,
            gameMode="CLASSIC",
            gameType="MATCHED_GAME",
            gameQueueConfigId=420,
            participants=[],
            observers={"encryptionKey": "test"},
            platformId="EUW1"
        )

        featured = FeaturedGamesDTO(
            gameList=[game],
            clientRefreshInterval=300
        )

        assert len(featured.game_list) == 1
        assert featured.client_refresh_interval == 300

    def test_featured_games_field_alias(self):
        """Test field alias works correctly."""
        data = {
            "gameList": [],
            "clientRefreshInterval": 300
        }

        featured = FeaturedGamesDTO(**data)
        assert featured.game_list == []
        assert featured.client_refresh_interval == 300


class TestActiveShardDTO:
    """Test cases for ActiveShardDTO."""

    def test_valid_active_shard(self):
        """Test creating valid active shard."""
        shard = ActiveShardDTO(
            puuid="test-puuid",
            game="lol",
            activeShard="europe"
        )

        assert shard.puuid == "test-puuid"
        assert shard.game == "lol"
        assert shard.active_shard == "europe"

    def test_active_shard_field_alias(self):
        """Test field alias works correctly."""
        data = {
            "puuid": "test-puuid",
            "game": "lol",
            "activeShard": "europe"
        }

        shard = ActiveShardDTO(**data)
        assert shard.puuid == "test-puuid"
        assert shard.game == "lol"
        assert shard.active_shard == "europe"