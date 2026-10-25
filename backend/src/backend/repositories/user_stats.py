from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user_stats import UserStats
from backend.repositories.base import BaseRepository


class UserStatsRepository(BaseRepository[UserStats]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserStats, session)

    async def get_by_user_id(self, user_id: bytes) -> UserStats | None:
        return await self.get_one_or_none(UserStats.user_id == user_id)
