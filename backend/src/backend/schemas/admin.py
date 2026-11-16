from datetime import datetime

from backend.models.user import OAuthProvider, UserRole
from backend.schemas.user import UserResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminUserResponse(UserResponse):
    """What a game master sees about a user."""

    oauth_provider: OAuthProvider
    two_factor_enabled: bool
    is_online: bool
    last_seen_at: datetime | None = None


class AdminUserListResponse(BaseModel):
    users: list[AdminUserResponse]
    total: int = Field(..., description="Matching users across all pages")


class AdminUserUpdateRequest(BaseModel):
    """Fields a game master may change; omitted fields stay as they are."""

    model_config = ConfigDict(str_strip_whitespace=True)
    username: str | None = Field(None, min_length=3, max_length=32)
    email: EmailStr | None = None
    avatar_url: str | None = Field(None, max_length=512)
    role: UserRole | None = None
