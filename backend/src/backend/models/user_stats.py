
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.user import User

class UserStats(Base):
    """
    Stores game performance statistics for each user.
    1-to-1 relationship with User.
    """
    __tablename__ = "user_stats"

    # Foreign Key & Primary Key pointing to users.id
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    matches_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    draws: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating_elo: Mapped[int] = mapped_column(BigInteger, default=1200, nullable=False)
    highest_scoring_word: Mapped[str | None] = mapped_column(String(32), nullable=True)
    highest_word_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_damage_dealt: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # relationship back to User
    user: Mapped["User"] = relationship("User", back_populates="stats")

