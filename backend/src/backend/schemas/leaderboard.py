from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EloLeaderboardEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int = Field(..., description="1-based rank position on the leaderboard")
    user_id: str = Field(..., description="User ID as UUID string")
    username: str = Field(..., description="Player username")
    avatar_url: str | None = Field(default=None, description="Player avatar URL")
    elo: int = Field(..., description="Current Elo rating")


class EloLeaderboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[EloLeaderboardEntry]
    total: int
    limit: int
    offset: int


class WordLeaderboardEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int = Field(..., description="1-based rank position on the leaderboard")
    word: str = Field(..., description="Word played in the match")
    score: int = Field(..., description="Score or damage value dealt by the word")
    user_id: str = Field(..., description="User ID of the player who played the word")
    username: str = Field(..., description="Username of the player")
    match_id: str = Field(..., description="Match ID as UUID string")
    played_at: datetime = Field(..., description="Timestamp when the word was played")


class WordLeaderboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[WordLeaderboardEntry]
    total: int
    limit: int
    offset: int


class DamageLeaderboardEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int = Field(..., description="1-based rank position on the leaderboard")
    user_id: str = Field(..., description="User ID as UUID string")
    username: str = Field(..., description="Player username")
    total_damage: int = Field(
        ..., description="Lifetime total damage dealt across matches"
    )
    matches_played: int | None = Field(default=None, description="Total matches played")


class DamageLeaderboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[DamageLeaderboardEntry]
    total: int
    limit: int
    offset: int
