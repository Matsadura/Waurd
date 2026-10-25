from backend.models.match import Match
from backend.repositories.base import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession


class MatchRepository(BaseRepository[Match]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Match, session)

    async def get_by_id(self, match_id: bytes) -> Match | None:
        return await self.get_one_or_none(Match.id == match_id)

    async def get_all_matches_for_user(self, user_id: bytes) -> list[Match]:
        return await self.list(
            (Match.player1_id == user_id) | (Match.player2_id == user_id),
            order_by=[Match.created_at.desc()],
        )
