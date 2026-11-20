from datetime import datetime

from backend.core.identifiers import user_id_to_string
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MatchResponse(BaseModel):
    """Response payload for match data."""

    model_config = ConfigDict(from_attributes=True)
    id: str = Field(..., description="Unique identifier for the match")
    player1_id: str = Field(..., description="Unique identifier for player 1")
    player2_id: str | None = Field(
        None, description="Unique identifier for player 2 (empty while waiting)"
    )
    time_control_seconds: int = Field(
        ..., description="Time control for the match in seconds"
    )
    status: str = Field(..., description="Current status of the match")
    end_reason: str | None = Field(
        None, description="Reason for match ending (if applicable)"
    )
    winner_id: str | None = Field(
        None, description="Unique identifier for the winner (if applicable)"
    )
    player1_final_hp: int | None = Field(
        None, description="Final health points of player 1 (if applicable)"
    )
    player2_final_hp: int | None = Field(
        None, description="Final health points of player 2 (if applicable)"
    )
    total_turns: int | None = Field(
        None, description="Total number of turns taken in the match"
    )
    duration_seconds: int | None = Field(
        None, description="Total duration of the match in seconds"
    )
    started_at: datetime | None = Field(
        None, description="Timestamp when the match started (if applicable)"
    )
    ended_at: datetime | None = Field(
        None, description="Timestamp when the match ended (if applicable)"
    )
    player1_elo_before: int | None = Field(
        None, description="Player 1's rating before the match (once it ended)"
    )
    player1_elo_after: int | None = Field(
        None, description="Player 1's rating after the match (once it ended)"
    )
    player2_elo_before: int | None = Field(
        None, description="Player 2's rating before the match (once it ended)"
    )
    player2_elo_after: int | None = Field(
        None, description="Player 2's rating after the match (once it ended)"
    )

    @field_validator("id", "player1_id", "player2_id", "winner_id", mode="before")
    @classmethod
    def serialize_ids(cls, value: bytes | str | None) -> str | None:
        return None if value is None else user_id_to_string(value)
