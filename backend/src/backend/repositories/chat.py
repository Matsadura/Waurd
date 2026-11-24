from backend.models.chat import ChannelType, ChatMessage
from backend.repositories.base import BaseRepository
from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class ChatRepository(BaseRepository[ChatMessage]):
    """Chat history, newest message first."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ChatMessage, session)

    async def global_messages(
        self, skip: int, limit: int
    ) -> tuple[list[ChatMessage], int]:
        return await self._page(
            ChatMessage.channel_type == ChannelType.GLOBAL, skip, limit
        )

    async def direct_messages(
        self, user_a: bytes, user_b: bytes, skip: int, limit: int
    ) -> tuple[list[ChatMessage], int]:
        between = or_(
            and_(ChatMessage.sender_id == user_a, ChatMessage.receiver_id == user_b),
            and_(ChatMessage.sender_id == user_b, ChatMessage.receiver_id == user_a),
        )
        condition = and_(ChatMessage.channel_type == ChannelType.DIRECT, between)
        return await self._page(condition, skip, limit)

    async def match_messages(
        self, match_id: bytes, skip: int, limit: int
    ) -> tuple[list[ChatMessage], int]:
        condition = and_(
            ChatMessage.channel_type == ChannelType.MATCH,
            ChatMessage.match_id == match_id,
        )
        return await self._page(condition, skip, limit)

    async def _page(
        self, condition: ColumnElement[bool], skip: int, limit: int
    ) -> tuple[list[ChatMessage], int]:
        total = (
            await self.session.execute(
                select(func.count()).select_from(ChatMessage).where(condition)
            )
        ).scalar_one()
        stmt = (
            select(ChatMessage)
            .options(selectinload(ChatMessage.sender))
            .where(condition)
            .order_by(ChatMessage.id.desc())
            .offset(skip)
            .limit(limit)
        )
        messages = list((await self.session.execute(stmt)).scalars().all())
        return messages, total
