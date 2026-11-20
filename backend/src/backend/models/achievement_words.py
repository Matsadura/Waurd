from datetime import datetime

from sqlalchemy import (
    BINARY,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class AchievementWord(Base):
    """A word in an achievement's collection. Achievement words also count as
    valid when spelled, even if the dictionary lacks them."""

    __tablename__ = "achievement_words"

    achievement_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("achievements.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # Uppercase, like glyph letters.
    word: Mapped[str] = mapped_column(String(32), primary_key=True)


class UserAchievementWord(Base):
    """A collection word a user has played; the achievement completes when
    they have played all of its words."""

    __tablename__ = "user_achievement_words"
    __table_args__ = (
        ForeignKeyConstraint(
            ["achievement_id", "word"],
            ["achievement_words.achievement_id", "achievement_words.word"],
            ondelete="CASCADE",
            name="fk_user_achievement_words_word",
        ),
    )

    user_id: Mapped[bytes] = mapped_column(
        BINARY(16),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    achievement_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    word: Mapped[str] = mapped_column(String(32), primary_key=True)
    found_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), default=datetime.utcnow, nullable=False
    )
