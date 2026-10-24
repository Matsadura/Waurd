import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import TIMESTAMP, BigInteger, Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.user import User


class ChannelType(str, enum.Enum):
    DIRECT = "DIRECT"
    GLOBAL = "GLOBAL"
    MATCH = "MATCH"


class ChatMessage(Base):
    """
    Stores direct, global, and in-match chat messages exchanged by users.
    """

    __tablename__ = "chat_messages"

    # Unique message ID (Auto-incrementing BigInteger: 1, 2, 3...)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # FK 1: Sender -> references users.id (String 36)
    sender_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # The global chat for testing purposes. will be removed .
    # FK 2: Receiver -> references users.id (Optional for GLOBAL/MATCH chat)
    receiver_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    channel_type: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType),
        default=ChannelType.DIRECT,
        nullable=False,
    )

    # Reference to a match ID if channel_type == MATCH
    match_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    message_content: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=datetime.utcnow, nullable=False
    )

    # Python relationships pointing back to User
    sender: Mapped["User"] = relationship(
        "User", foreign_keys=[sender_id], back_populates="sent_chat_messages"
    )
    receiver: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[receiver_id], back_populates="received_chat_messages"
    )
