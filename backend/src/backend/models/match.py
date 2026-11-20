import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    BINARY,
    JSON,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.user import User


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
    player1_id: Mapped[bytes] = mapped_column(
        BINARY(16),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    player2_id: Mapped[bytes | None] = mapped_column(
        BINARY(16),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    invite_code: Mapped[str | None] = mapped_column(
        String(6), nullable=True, unique=True, index=True
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
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Each player's rating before and after the match, filled when it ends.
    player1_elo_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player1_elo_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player2_elo_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player2_elo_after: Mapped[int | None] = mapped_column(Integer, nullable=True)

    player1: Mapped["User"] = relationship("User", foreign_keys=[player1_id])
    player2: Mapped[Optional["User"]] = relationship("User", foreign_keys=[player2_id])
    winner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[winner_id])
    casts: Mapped[list["MatchCast"]] = relationship(
        "MatchCast", back_populates="match", cascade="all, delete-orphan"
    )


class MatchCast(Base):
    __tablename__ = "match_casts"
    # One cast per turn: a retried write can't record the same turn twice.
    __table_args__ = (
        UniqueConstraint("match_id", "turn_number", name="uq_match_casts_match_turn"),
    )

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
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    match: Mapped["Match"] = relationship("Match", back_populates="casts")
    player: Mapped["User"] = relationship(
        "User",
    )
