from backend.core.identifiers import user_id_to_bytes
from backend.models.match import Match, MatchStatus
from backend.repositories.base import BaseRepository
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


class MatchRepository(BaseRepository[Match]):
    def __init__(self, session: AsyncSession):
        super().__init__(Match, session)

    async def get_active_match_for_user(self, user_id_bytes: bytes) -> Match | None:
        """Finds any ongoing match where the user is currently player1 or player2."""
        stmt = select(Match).where(
            Match.status.in_([MatchStatus.WAITING, MatchStatus.ACTIVE]),
            or_(
                Match.player1_id == user_id_bytes,
                Match.player2_id == user_id_bytes,
            ),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_pvp_match(
        self,
        match_id_str: str,
        player1_id_str: str,
        player2_id_str: str,
        time_control_seconds: int,
    ) -> Match:
        """Persists a newly paired PVP match to MySQL using BINARY(16) UUID bytes."""
        match = Match(
            id=user_id_to_bytes(match_id_str),
            player1_id=user_id_to_bytes(player1_id_str),
            player2_id=user_id_to_bytes(player2_id_str),
            status=MatchStatus.ACTIVE,
            time_control_seconds=time_control_seconds,
        )
        self.session.add(match)
        await self.session.flush()
        return match 
