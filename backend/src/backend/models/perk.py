import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.achievements import Achievement


class TargetGlyphType(str, enum.Enum):
    """Which glyphs a perk goes on (catalog.csv's target_type)."""

    DAMAGE = "DAMAGE"
    HEAL_DEFENSE = "HEAL_DEFENSE"  # heal or defense glyphs
    ANY = "ANY"


class ModificationType(str, enum.Enum):
    """What a perk changes, to group perks in the UI. The rule itself is the
    perk's function in game/perks/effects.py."""

    EFFECT = "EFFECT"  # e.g. Damage -> Heal
    TYPE = "TYPE"  # e.g. Power -> Skill
    POWER_VALUE = "POWER_VALUE"  # raise, lower, double, halve the effect value
    CONDITIONAL_SLOT = "CONDITIONAL_SLOT"  # bonus slot, e.g. "x2 if last letter"
    LETTERS = "LETTERS"  # transform the glyph's letters, e.g. -ING-, -ER-
    DECK = "DECK"  # change the deck itself, e.g. Erase


class Rarity(str, enum.Enum):
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    LEGENDARY = "LEGENDARY"


class Perk(Base):
    """
    Catalog of Perks that modify Glyphs in Waurd.
    """

    __tablename__ = "perks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(120), nullable=False)
    quote: Mapped[str | None] = mapped_column(String(120), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    rarity: Mapped[Rarity] = mapped_column(Enum(Rarity), nullable=False, index=True)
    target_glyph_type: Mapped[TargetGlyphType] = mapped_column(
        Enum(TargetGlyphType), nullable=False
    )
    modification_type: Mapped[ModificationType] = mapped_column(
        Enum(ModificationType), nullable=False
    )
    # NULL means unlimited (achievement perks may never break).
    durability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # {"mechanics": ...}: the catalog's plain-text rule, for reference; the
    # behaviour is the perk's function in game/perks/effects.py
    effect_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Only enabled perks are offered in drafts ("ready" in the perk sheet).
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )  # TBD
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    achievements: Mapped[list["Achievement"]] = relationship(
        "Achievement", back_populates="reward_perk"
    )
