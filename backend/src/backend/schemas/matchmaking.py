import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.game.config import DEFAULT_CONFIG

# The game engine's time controls, in seconds per player.
TIME_CONTROLS = DEFAULT_CONFIG.time_controls
DEFAULT_TIME_CONTROL = 300


class TimeControl(int, enum.Enum):
    BLITZ = 180
    STANDARD = 300
    RELAXED = 600


def _spoken(values: tuple[int, ...]) -> str:
    *rest, last = (str(v) for v in values)
    return f"{', '.join(rest)} or {last}" if rest else last


def check_time_control(time: int) -> int:
    if time not in TIME_CONTROLS:
        raise ValueError(f"Time control must be {_spoken(TIME_CONTROLS)} seconds.")
    return time


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
        ..., description="Time control per player in seconds (180, 300 or 600)"
    )

    @field_validator("time_control_seconds")
    @classmethod
    def validate_time_control(cls, time: int) -> int:
        return check_time_control(time)


class QueueLeaveRequest(BaseModel):
    time_control_seconds: int = Field(
        ..., description="Time control per player in seconds (180, 300 or 600)"
    )

    @field_validator("time_control_seconds")
    @classmethod
    def validate_time_control(cls, time: int) -> int:
        return check_time_control(time)


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
    time_control_seconds: int = Field(
        DEFAULT_TIME_CONTROL, description="180, 300 or 600 seconds"
    )

    @field_validator("time_control_seconds")
    @classmethod
    def validate_time_control(cls, time: int) -> int:
        return check_time_control(time)


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
