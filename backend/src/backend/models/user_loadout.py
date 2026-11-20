from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BINARY, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.perk import Perk
    from backend.models.user import User


class UserLoadout(Base):
    """
    Stores persistent starter perks equipped by a user before queuing.
    """

    __tablename__ = "user_loadouts"

    user_id: Mapped[bytes] = mapped_column(
        BINARY(16),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    perk_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("perks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), default=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="loadout")
    perk: Mapped["Perk"] = relationship("Perk")
