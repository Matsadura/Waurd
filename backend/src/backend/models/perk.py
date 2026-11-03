import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.achievements import Achievement


class TargetGlyphType(str, enum.Enum):
    POWER = "POWER"
    SKILL = "SKILL"
    ANY = "ANY"


class ModificationType(str, enum.Enum):
    EFFECT = "EFFECT"
    TYPE = "TYPE"
    POWER_VALUE = "POWER_VALUE"
    CONDITIONAL_SLOT = "CONDITIONAL_SLOT"


class Perk(Base):
    """
    Catalog of Perks that modify Glyphs in Waurd.
    """

    __tablename__ = "perks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    target_glyph_type: Mapped[TargetGlyphType] = mapped_column(
        Enum(TargetGlyphType), nullable=False
    )
    modification_type: Mapped[ModificationType] = mapped_column(
        Enum(ModificationType), nullable=False
    )
    default_durability: Mapped[int] = mapped_column(Integer, nullable=False)
    effect_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    achievements: Mapped[list["Achievement"]] = relationship(
        "Achievement", back_populates="reward_perk"
    )
