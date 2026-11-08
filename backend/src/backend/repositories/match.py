import secrets
import string
import uuid

from backend.core.identifiers import user_id_to_bytes
from backend.models.match import Match, MatchStatus
from backend.repositories.base import BaseRepository
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
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

    async def create_custom_match(
        self,
        creator_id_bytes: bytes,
        time_control_seconds: int,
    ) -> Match:
        """Creates a custom match lobby with an optional 6-character room code."""
        alphabet = string.ascii_uppercase + string.digits
        invite_code = "".join(secrets.choice(alphabet) for _ in range(6))

        match = Match(
            id=uuid.uuid4().bytes,
            player1_id=creator_id_bytes,
            player2_id=None,
            status=MatchStatus.WAITING,
            time_control_seconds=time_control_seconds,
            invite_code=invite_code,
        )
        self.session.add(match)
        await self.session.flush()
        await self.session.refresh(match)
        return match

    async def join_match_by_code(
        self,
        joiner_id_bytes: bytes,
        invite_code: str,
    ) -> Match:
        """Finds a WAITING lobby by invite code, assigns player2_id, and activates the match."""
        stmt = select(Match).where(
            Match.invite_code == invite_code.upper(),
            Match.status == MatchStatus.WAITING,
        )
        result = await self.session.execute(stmt)
        match = result.scalar_one_or_none()

        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired invite code.",
            )

        if match.player1_id == joiner_id_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot join your own custom match lobby.",
            )

        match.player2_id = joiner_id_bytes
        match.status = MatchStatus.ACTIVE
        match.started_at = func.now()

        await self.session.flush()
        await self.session.refresh(match)
        return match

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
        await self.session.refresh(match)
        return match

    async def create_ai_match(
        self,
        player_id_bytes: bytes,
        ai_difficulty: str,
        time_control_seconds: int,
    ) -> Match:
        """Instantiates an active match against an AI bot."""
        match = Match(
            id=uuid.uuid4().bytes,
            player1_id=player_id_bytes,
            player2_id=None,
            is_ai_match=1,
            ai_difficulty=ai_difficulty,
            status=MatchStatus.ACTIVE,
            time_control_seconds=time_control_seconds,
        )
        self.session.add(match)
        await self.session.flush()
        await self.session.refresh(match)
        return match
