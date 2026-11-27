from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.game.balance import MAX_LOADOUT_SLOTS
from backend.models.perk import ModificationType, Rarity, TargetGlyphType


class PerkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    quote: str | None = None
    image_url: str | None = None
    rarity: Rarity
    target_glyph_type: TargetGlyphType
    modification_type: ModificationType
    durability: int | None = None
    is_enabled: bool = False
    effect_payload: dict[str, Any] = Field(default_factory=dict)


class AchievementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    icon_url: str
    xp_reward: int
    target_value: int
    reward_perk_id: str | None = None
    reward_perk: PerkResponse | None = None


class UserAchievementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    achievement_id: str
    name: str
    description: str
    icon_url: str
    xp_reward: int
    target_value: int
    current_progress: int
    is_completed: bool
    progress_percentage: float
    unlocked_at: datetime | None = None
    reward_perk_id: str | None = None
    reward_perk: PerkResponse | None = None


class UserLoadoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    max_slots: int = MAX_LOADOUT_SLOTS
    equipped_perks: list[PerkResponse]
    unlocked_perks: list[PerkResponse]


class UpdateLoadoutRequest(BaseModel):
    perk_ids: list[str] = Field(
        ...,
        max_length=MAX_LOADOUT_SLOTS,
        description=f"List of up to {MAX_LOADOUT_SLOTS} perk IDs to equip in active starter loadout",
    )

    @field_validator("perk_ids")
    @classmethod
    def validate_unique_perks(cls, v: list[str]) -> list[str]:
        if len(v) > MAX_LOADOUT_SLOTS:
            raise ValueError(
                f"You can equip at most {MAX_LOADOUT_SLOTS} perks in your loadout."
            )
        if len(v) != len(set(v)):
            raise ValueError("Duplicate perks are not allowed in loadout.")
        return v
