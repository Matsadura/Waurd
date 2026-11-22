from backend.models.user_stats import DEFAULT_RATING, UserStats
from backend.repositories.base import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession


class UserStatsRepository(BaseRepository[UserStats]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserStats, session)

    async def get_by_user_id(self, user_id: bytes) -> UserStats | None:
        return await self.get_one_or_none(UserStats.user_id == user_id)

    async def get_rating(self, user_id: bytes) -> int:
        """The user's Elo rating, or the starting rating if they have no stats row."""
        stats = await self.get_by_user_id(user_id)
        return DEFAULT_RATING if stats is None else stats.rating_elo
