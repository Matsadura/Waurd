from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.perk import Perk
    from backend.models.user_achievements import UserAchievement


class Achievement(Base):
    """
    Represents an achievement that can be unlocked by users.
    """

    __tablename__ = "achievements"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    icon_url: Mapped[str] = mapped_column(String(255), nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    reward_perk_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("perks.id", ondelete="SET NULL"), nullable=True
    )
    target_value: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Python standard datetime is used for Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships using lazy string resolution
    user_achievements: Mapped[list["UserAchievement"]] = relationship(
        "UserAchievement", back_populates="achievement", cascade="all, delete-orphan"
    )
    reward_perk: Mapped[Optional["Perk"]] = relationship(
        "Perk", back_populates="achievements"
    )