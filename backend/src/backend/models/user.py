import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BINARY, TIMESTAMP, Boolean, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin
from backend.models.chat import ChatMessage
from backend.models.friendship import Friendship
from backend.models.user_achievements import UserAchievement
from backend.models.user_stats import UserStats

if TYPE_CHECKING:
    from backend.models.tournament import Tournament, TournamentParticipant


class OAuthProvider(str, enum.Enum):
    LOCAL = "LOCAL"
    GOOGLE = "GOOGLE"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[bytes] = mapped_column(
        BINARY(16),
        primary_key=True,
        default=lambda: uuid.uuid4().bytes,
    )

    username: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    oauth_provider: Mapped[OAuthProvider] = mapped_column(
        Enum(OAuthProvider, values_callable=lambda obj: [e.value for e in obj]),
        default=OAuthProvider.LOCAL,
        nullable=False,
    )
    oauth_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    two_factor_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    two_factor_secret: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )  # Might Remove if not needed

    xp: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    elo: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    level: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    is_online: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        nullable=True,
    )
    # relationships stats and achievements
    stats: Mapped[Optional["UserStats"]] = relationship(
        "UserStats", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    achievements: Mapped[list["UserAchievement"]] = relationship(
        "UserAchievement", back_populates="user", cascade="all, delete-orphan"
    )

    # Sent and Received Friend Requests
    sent_friend_requests: Mapped[list["Friendship"]] = relationship(
        "Friendship",
        foreign_keys="[Friendship.requester_id]",
        back_populates="requester",
        cascade="all, delete-orphan",
    )
    received_friend_requests: Mapped[list["Friendship"]] = relationship(
        "Friendship",
        foreign_keys="[Friendship.addressee_id]",
        back_populates="addressee",
        cascade="all, delete-orphan",
    )
    # Sent and Received Chat Messages
    sent_chat_messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        foreign_keys="[ChatMessage.sender_id]",
        back_populates="sender",
        cascade="all, delete-orphan",
    )
    received_chat_messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        foreign_keys="[ChatMessage.receiver_id]",
        back_populates="receiver",
        cascade="all, delete-orphan",
    )
    created_tournaments: Mapped[list["Tournament"]] = relationship(
        "Tournament",
        foreign_keys="[Tournament.created_by]",
        back_populates="creator",
        cascade="all, delete-orphan",
    )
    won_tournaments: Mapped[list["Tournament"]] = relationship(
        "Tournament",
        foreign_keys="[Tournament.winner_id]",
        back_populates="winner",
    )
    tournament_participations: Mapped[list["TournamentParticipant"]] = relationship(
        "TournamentParticipant",
        back_populates="user",
        cascade="all, delete-orphan",
    )
