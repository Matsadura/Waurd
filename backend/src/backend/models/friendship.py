import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BINARY,
    TIMESTAMP,
    BigInteger,
    Enum,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.user import User


class FriendshipStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    BLOCKED = "BLOCKED"


class Friendship(Base):
    """
    Represents a directional friendship/block relationship between two users.
    """

    __tablename__ = "friendships"

    # Unique constraint ensures User A can only send one friend request to User B at a time
    __table_args__ = (
        UniqueConstraint(
            "requester_id", "addressee_id", name="uq_friendship_requester_addressee"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    requester_id: Mapped[bytes] = mapped_column(
        BINARY(16),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    addressee_id: Mapped[bytes] = mapped_column(
        BINARY(16),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[FriendshipStatus] = mapped_column(
        Enum(FriendshipStatus),
        default=FriendshipStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships pointing back to User
    requester: Mapped["User"] = relationship(
        "User", foreign_keys=[requester_id], back_populates="sent_friend_requests"
    )
    addressee: Mapped["User"] = relationship(
        "User", foreign_keys=[addressee_id], back_populates="received_friend_requests"
    )
