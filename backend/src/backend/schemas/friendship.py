import enum
from datetime import datetime

from backend.models.friendship import FriendshipStatus
from pydantic import BaseModel, ConfigDict, Field, model_validator


class FriendUserResponse(BaseModel):
    id: str = Field(..., description="User UUID string")
    username: str
    avatar_url: str | None = None
    is_online: bool
    last_seen_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class FriendshipResponse(BaseModel):
    id: int
    requester_id: str
    addressee_id: str
    status: FriendshipStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FriendRequestCreate(BaseModel):
    target_user_id: str | None = Field(None, description="Target user UUID string")
    username: str | None = Field(None, description="Target username")

    @model_validator(mode="after")
    def validate_target(self):
        if not self.target_user_id and not self.username:
            raise ValueError("Either target_user_id or username must be provided.")
        return self


class RequestAction(str, enum.Enum):
    ACCEPT = "ACCEPTED"
    DECLINE = "DECLINED"


class FriendRequestUpdate(BaseModel):
    action: RequestAction


class FriendListResponse(BaseModel):
    """Response schema for GET /friends."""

    friends: list[FriendUserResponse]


class PendingRequestsResponse(BaseModel):
    """Response schema for pending friend requests."""

    incoming: list[FriendUserResponse]
    outgoing: list[FriendUserResponse]
