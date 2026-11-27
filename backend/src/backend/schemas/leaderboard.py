import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LeaderboardFilter(enum.StrEnum):
    """What ?filter_by= ranks on."""

    ELO = "elo"
    WORDS = "words"
    DAMAGE = "damage"
    WIN_STREAK = "win_streak"


class PlayerLeaderboardEntry(BaseModel):
    """One player on the elo, damage or win_streak board."""

    model_config = ConfigDict(from_attributes=True)

    rank: int = Field(..., description="1-based rank position on the leaderboard")
    user_id: str = Field(..., description="User ID as UUID string")
    username: str = Field(..., description="Player username")
    avatar_url: str | None = Field(default=None, description="Player avatar URL")
    value: int = Field(
        ...,
        description="What the board ranks on: Elo rating, lifetime damage or "
        "best win streak",
    )
    matches_played: int = Field(..., description="Total matches played")


class WordLeaderboardEntry(BaseModel):
    """One cast on the words board."""

    model_config = ConfigDict(from_attributes=True)

    rank: int = Field(..., description="1-based rank position on the leaderboard")
    word: str = Field(..., description="Word played in the match")
    score: int = Field(..., description="Score or damage value dealt by the word")
    user_id: str = Field(..., description="User ID of the player who played the word")
    username: str = Field(..., description="Username of the player")
    match_id: str = Field(..., description="Match ID as UUID string")
    played_at: datetime = Field(..., description="Timestamp when the word was played")


class LeaderboardResponse(BaseModel):
    filter_by: LeaderboardFilter
    # words entries for filter_by=words, player entries for the others
    items: list[WordLeaderboardEntry] | list[PlayerLeaderboardEntry]
    total: int
    limit: int
    offset: int
