from typing import TYPE_CHECKING

from sqlalchemy import BINARY, BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.user import User


DEFAULT_RATING = 1200


class UserStats(Base):
    """
    Stores game performance statistics for each user.
    1-to-1 relationship with User.
    """

    __tablename__ = "user_stats"

    # Foreign Key & Primary Key pointing to users.id
    user_id: Mapped[bytes] = mapped_column(
        BINARY(16),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    matches_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    draws: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # The one Elo rating; the leaderboard sorts on it.
    rating_elo: Mapped[int] = mapped_column(
        Integer,
        default=DEFAULT_RATING,
        server_default=str(DEFAULT_RATING),
        nullable=False,
        index=True,
    )
    highest_scoring_word: Mapped[str | None] = mapped_column(String(32), nullable=True)
    highest_word_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_damage_dealt: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )
    # wins in a row up to now (a loss resets it), and the longest run ever
    win_streak: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    best_win_streak: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False, index=True
    )
    # the most HP one cast has given back
    highest_heal: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False, index=True
    )

    # relationship back to User
    user: Mapped["User"] = relationship("User", back_populates="stats")
