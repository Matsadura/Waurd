import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TimeControl(int, enum.Enum):
    BULLET = 60
    BLITZ = 180
    RAPID = 300


class MatchStatusEnum(str, enum.Enum):
    WAITING = "WAITING"
    ACTIVE = "ACTIVE"
    FINISHED = "FINISHED"
    ABANDONED = "ABANDONED"


class QueueStatusEnum(str, enum.Enum):
    QUEUED = "QUEUED"
    CLAIMING = "CLAIMING"
    MATCHED = "MATCHED"
    CANCELLED = "CANCELLED"
    WAITING = "WAITING"
    ACTIVE = "ACTIVE"


class QueueJoinRequest(BaseModel):
    time_control_seconds: int = Field(
        ..., description="Time control per player in seconds (60, 180, 300)"
    )

    @field_validator("time_control_seconds")
    @classmethod
    def validate_time_control(cls, time: int) -> int:
        if time not in (60, 180, 300):
            raise ValueError("time_control_seconds must be 60, 180, or 300 seconds.")
        return time


class QueueLeaveRequest(BaseModel):
    time_control_seconds: int = Field(
        ..., description="Time control per player in seconds (60, 180, 300)"
    )

    @field_validator("time_control_seconds")
    @classmethod
    def validate_time_control(cls, time: int) -> int:
        if time not in (60, 180, 300):
            raise ValueError("time_control_seconds must be 60, 180, or 300 seconds.")
        return time


class QueueTicketResponse(BaseModel):
    ticket_id: str
    user_id: str
    time_control_seconds: int
    status: QueueStatusEnum
    queued_at: datetime
    matched_match_id: str | None = None
    elo: int | None = None

    model_config = ConfigDict(from_attributes=True)


class CustomMatchCreateRequest(BaseModel):
    time_control_seconds: int = Field(180, description="60, 180, or 300 seconds")

    @field_validator("time_control_seconds")
    @classmethod
    def validate_time_control(cls, time: int) -> int:
        if time not in (60, 180, 300):
            raise ValueError("time_control_seconds must be 60, 180, or 300 seconds.")
        return time


class MatchPlayerResponse(BaseModel):
    id: str
    username: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CustomMatchResponse(BaseModel):
    id: str
    invite_code: str | None
    status: MatchStatusEnum
    time_control_seconds: int
    is_private: bool = False
    creator: MatchPlayerResponse
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JoinMatchRequest(BaseModel):
    invite_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="6-character uppercase invite code",
    )


class MatchDetailResponse(BaseModel):
    id: str
    invite_code: str | None = None
    status: MatchStatusEnum
    time_control_seconds: int
    player1: MatchPlayerResponse
    player2: MatchPlayerResponse | None = None
    winner_id: str | None = None
    end_reason: str | None = None
    player1_final_hp: int | None = None
    player2_final_hp: int | None = None
    total_turns: int = 0
    duration_seconds: int = 0
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MatchCastResponse(BaseModel):
    id: str
    match_id: str
    turn_number: int
    player_id: str
    word_played: str
    glyphs_payload: dict[str, Any] = Field(default_factory=dict)
    status_effects_applied: dict[str, Any] | None = None
    damage_dealt: int = 0
    defense_gained: int = 0
    heal_amount: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
