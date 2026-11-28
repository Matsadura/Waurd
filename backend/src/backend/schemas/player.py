"""Another player's public profile: only what any signed-in player may see."""

from datetime import datetime

from backend.core.identifiers import user_id_to_string
from backend.game.calculations import level_progress, xp_to_next
from backend.schemas.user import UserStatsResponse
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class PublicAchievement(BaseModel):
    """A completed achievement."""

    achievement_id: str
    name: str
    description: str
    icon_url: str
    xp_reward: int
    unlocked_at: datetime


class PublicPlayerResponse(BaseModel):
    """No email, role, sign-in or 2FA details: those stay in /users."""

    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    avatar_url: str | None = None
    created_at: datetime
    xp: int = Field(..., exclude=True)  # only the level and progress are shown
    level: int
    # online status is shown to friends only, as in GET /friends; null otherwise
    is_online: bool | None = None
    last_seen_at: datetime | None = None
    stats: UserStatsResponse | None = Field(
        None, description="Null for a player with no stats yet"
    )
    achievements: list[PublicAchievement] = Field(
        default_factory=list, description="Completed ones, most recent first"
    )

    @computed_field(description="XP earned since reaching the current level")
    @property
    def xp_into_level(self) -> int:
        return level_progress(self.xp)[1]

    @computed_field(description="XP the current level takes to reach the next")
    @property
    def xp_for_next_level(self) -> int:
        return xp_to_next(level_progress(self.xp)[0])

    @field_validator("id", mode="before")
    @classmethod
    def serialize_id(cls, value: bytes | str) -> str:
        return user_id_to_string(value)
