import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TimeControl(int, enum.Enum):
    BULLET = 60
    BLITZ = 180
    RAPID = 300


class MatchStatusEnum(str, enum.Enum):
    WAITING = "WAITING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class QueueStatusEnum(str, enum.Enum):
    QUEUED = "QUEUED"
    MATCHED = "MATCHED"
    CANCELLED = "CANCELLED"


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


class CustomMatchCreateRequest(BaseModel):
    time_control_seconds: int = Field(180, description="60, 180, or 300 seconds")


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
    creator: MatchPlayerResponse
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
