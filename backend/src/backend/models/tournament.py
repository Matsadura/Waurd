import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BINARY, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.match import Match
    from backend.models.user import User


class TournamentStatus(str, enum.Enum):
    REGISTRATION = "REGISTRATION"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[bytes] = mapped_column(BINARY(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    max_participants: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[TournamentStatus] = mapped_column(
        Enum(TournamentStatus),
        default=TournamentStatus.REGISTRATION,
        nullable=False,
    )

    winner_id: Mapped[bytes | None] = mapped_column(
        BINARY(16),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[bytes] = mapped_column(
        BINARY(16),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    creator: Mapped["User"] = relationship(
        "User", foreign_keys=[created_by], back_populates="created_tournaments"
    )
    winner: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[winner_id], back_populates="won_tournaments"
    )
    participants: Mapped[list["TournamentParticipant"]] = relationship(
        "TournamentParticipant", back_populates="tournament", cascade="all, delete-orphan"
    )
    matches: Mapped[list["Match"]] = relationship(
        "Match", back_populates="tournament", cascade="all, delete-orphan"
    )


class TournamentParticipant(Base):
    __tablename__ = "tournament_participants"

    tournament_id: Mapped[bytes] = mapped_column(
        BINARY(16),
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[bytes] = mapped_column(
        BINARY(16),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    seed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    joined_at: Mapped[DateTime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="participants")
    user: Mapped["User"] = relationship("User", back_populates="tournament_participations")