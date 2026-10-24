from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.achievements import Achievement
    from backend.models.user import User

class UserAchievement(Base):
    """
    Table to track which achievements have been unlocked by which users.
    Many-to-many relationship between User and Achievement.
    """
    __tablename__ = "user_achievements"

    # Primary key user_id references users.id as foreign key
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # primary key achievement_id references achievements.id as foreign key
    achievement_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("achievements.id", ondelete="CASCADE"),
        primary_key=True,
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationship to User and Achievement
    user: Mapped["User"] = relationship("User", back_populates="achievements")
    achievement: Mapped["Achievement"] = relationship(
        "Achievement", back_populates="user_achievements"
    )