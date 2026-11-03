from datetime import datetime

from backend.core.identifiers import user_id_to_string
from pydantic import BaseModel, ConfigDict, Field


class MatchResponse(BaseModel):
    """Response payload for match data."""

    model_config = ConfigDict(from_attributes=True)
    id: str = Field(..., description="Unique identifier for the match")
    tournament_id: str | None = Field(
        None, description="Unique identifier for the tournament (if applicable)"
    )
    player1_id: str = Field(..., description="Unique identifier for player 1")
    player2_id: str = Field(..., description="Unique identifier for player 2")
    is_ai_match: bool = Field(
        ..., description="Indicates if the match is against an AI opponent"
    )
    ai_difficulty: str | None = Field(
        None, description="Difficulty level of the AI opponent (if applicable)"
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
