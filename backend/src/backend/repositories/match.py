import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta

from backend.core.exceptions import (
    BadRequestException,
    EntityNotFoundException,
    ForbiddenException,
)
from backend.core.identifiers import user_id_to_bytes
from backend.models.match import Match, MatchCast, MatchStatus
from backend.repositories.base import BaseRepository
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


class MatchRepository(BaseRepository[Match]):
    def __init__(self, session: AsyncSession):
        super().__init__(Match, session)

    async def get_active_match_for_user(self, user_id_bytes: bytes) -> Match | None:
        """Finds active or waiting matches. Automatically marks WAITING lobbies
        older than 15 minutes as ABANDONED to unlock the user."""
        stmt = select(Match).where(
            Match.status.in_([MatchStatus.WAITING, MatchStatus.ACTIVE]),
            or_(
                Match.player1_id == user_id_bytes,
                Match.player2_id == user_id_bytes,
            ),
        )
        result = await self.session.execute(stmt)
        match = result.scalar_one_or_none()
        if not match:
            return None

        if match.status == MatchStatus.WAITING and match.created_at:
            created_at = (
                match.created_at.replace(tzinfo=UTC)
                if match.created_at.tzinfo is None
                else match.created_at
            )
            if (datetime.now(UTC) - created_at) > timedelta(minutes=15):
                match.status = MatchStatus.ABANDONED
                await self.session.flush()
                return None

        return match

    async def get_match_by_id(self, match_id_bytes: bytes) -> Match | None:
        """Fetches a match record by its BINARY(16) primary key."""
        stmt = select(Match).where(Match.id == match_id_bytes)
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
            raise EntityNotFoundException("Invalid or expired invite code")
        # 1. Validate lobby age (abandon if > 15 minutes old)
        if match.created_at:
            created_at = (
                match.created_at.replace(tzinfo=UTC)
                if match.created_at.tzinfo is None
                else match.created_at
            )
            if (datetime.now(UTC) - created_at) > timedelta(minutes=15):
                match.status = MatchStatus.ABANDONED
                await self.session.flush()
                await self.session.commit()
                raise EntityNotFoundException("Invalid or expired invite code.")
        if match.player1_id == joiner_id_bytes:
            raise BadRequestException("You cannot join your own custom match lobby")

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

    async def get_casts_for_match(self, match_id_bytes: bytes) -> list:
        """
        Retrieves all recorded turn casts for a match ordered chronologically by turn number.
        """
        # If storing turn logs in a related model/table (e.g., MatchCast or TurnLog)
        stmt = (
            select(MatchCast)
            .where(MatchCast.match_id == match_id_bytes)
            .order_by(MatchCast.turn_number.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def cancel_custom_match(
        self,
        match_id_bytes: bytes,
        user_id_bytes: bytes,
    ) -> Match:
        """
        Cancels a WAITING custom match lobby. Strictly restricted to the lobby creator.
        """
        stmt = select(Match).where(Match.id == match_id_bytes)
        result = await self.session.execute(stmt)
        match = result.scalar_one_or_none()

        if not match:
            raise EntityNotFoundException("Match lobby not found.")

        if match.player1_id != user_id_bytes:
            raise ForbiddenException("Only the lobby creator can cancel this match.")

        if match.status != MatchStatus.WAITING:
            raise BadRequestException(
                "Cannot cancel a match that is not in WAITING status."
            )

        match.status = MatchStatus.ABANDONED
        await self.session.flush()
        await self.session.refresh(match)
        return match

    async def abandon_active_match(
        self, match_id_bytes: bytes, user_id_bytes: bytes
    ) -> Match:
        """
        Abandons an ACTIVE match. This can be used in scenarios where a player leaves or disconnects.
        """
        stmt = select(Match).where(Match.id == match_id_bytes)
        result = await self.session.execute(stmt)
        match = result.scalar_one_or_none()

        if not match:
            raise EntityNotFoundException("Match not found.")

        if match.status != MatchStatus.ACTIVE:
            raise BadRequestException(
                "Cannot abandon a match that is not in ACTIVE status."
            )

        if user_id_bytes not in [match.player1_id, match.player2_id]:
            raise ForbiddenException("You are not a participant in this match.")

        match.status = MatchStatus.ABANDONED
        await self.session.flush()
        await self.session.refresh(match)
        return match
