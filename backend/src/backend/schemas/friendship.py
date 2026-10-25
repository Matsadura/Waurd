from datetime import datetime

from backend.models.friendship import FriendshipStatus
from pydantic import BaseModel, ConfigDict, Field


class FriendUserResponse(BaseModel):
    """User summary returned in friend list responses."""

    id: str = Field(..., description="User UUID string")
    username: str
    avatar_url: str | None = None
    is_online: bool
    last_seen_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class FriendshipResponse(BaseModel):
    """Response schema for friend request actions."""

    id: int
    requester_id: str
    addressee_id: str
    status: FriendshipStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FriendRequestCreate(BaseModel):
    """Input payload to send a friend request."""

    addressee_id: str = Field(..., description="Target user UUID string")


class FriendListResponse(BaseModel):
    """Response schema for GET /friends."""

    friends: list[FriendUserResponse]


class PendingRequestsResponse(BaseModel):
    """Response schema for pending friend requests."""

    incoming: list[FriendUserResponse]
    outgoing: list[FriendUserResponse]
