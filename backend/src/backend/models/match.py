import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    BINARY,
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.tournament import Tournament
    from backend.models.user import User


class AIDifficulty(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class MatchStatus(str, enum.Enum):
    WAITING = "WAITING"
    ACTIVE = "ACTIVE"
    FINISHED = "FINISHED"
    ABANDONED = "ABANDONED"


class MatchEndReason(str, enum.Enum):
    HEALTH_DEPLETED = "HEALTH_DEPLETED"
    TIMEOUT = "TIMEOUT"
    RESIGNATION = "RESIGNATION"
    DISCONNECT = "DISCONNECT"


class Match(Base, TimestampMixin):
    __tablename__ = "matches"

    id: Mapped[bytes] = mapped_column(BINARY(16), primary_key=True)
    tournament_id: Mapped[bytes | None] = mapped_column(
        BINARY(16),
        ForeignKey("tournaments.id", ondelete="SET NULL"),
        nullable=True,
    )
    tournament_round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player1_id: Mapped[bytes] = mapped_column(
        BINARY(16),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    player2_id: Mapped[bytes] = mapped_column(
        BINARY(16),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_ai_match: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_difficulty: Mapped[AIDifficulty | None] = mapped_column(
        Enum(AIDifficulty), nullable=True
    )
    time_control_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus), default=MatchStatus.WAITING, nullable=False
    )
    end_reason: Mapped[MatchEndReason | None] = mapped_column(
        Enum(MatchEndReason), nullable=True
    )
    winner_id: Mapped[bytes | None] = mapped_column(
        BINARY(16),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    player1_final_hp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player2_final_hp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_turns: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    tournament: Mapped[Optional["Tournament"]] = relationship(
        "Tournament", back_populates="matches"
    )
    player1: Mapped["User"] = relationship("User", foreign_keys=[player1_id])
    player2: Mapped["User"] = relationship("User", foreign_keys=[player2_id])
    winner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[winner_id])
    casts: Mapped[list["MatchCast"]] = relationship(
        "MatchCast", back_populates="match", cascade="all, delete-orphan"
    )


class MatchCast(Base):
    __tablename__ = "match_casts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    match_id: Mapped[bytes] = mapped_column(
        BINARY(16),
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    player_id: Mapped[bytes] = mapped_column(
        BINARY(16),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    word_played: Mapped[str] = mapped_column(String(32), nullable=False)
    damage_dealt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    defense_gained: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    heal_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status_effects_applied: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    glyphs_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    match: Mapped["Match"] = relationship("Match", back_populates="casts")
    player: Mapped["User"] = relationship(
        "User",
    )
