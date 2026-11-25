from typing import Any

from backend.core.identifiers import user_id_to_string
from backend.models.match import Match, MatchCast, MatchStatus
from backend.models.user import User
from backend.models.user_stats import DEFAULT_RATING, UserStats
from backend.repositories.base import BaseRepository
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class LeaderboardRepository(BaseRepository[User]):
    """Repository handling all leaderboard queries across players, words, and lifetime damage."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_elo_leaderboard(
        self, limit: int = 20, offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        """Fetch paginated players ranked by Elo rating (DESC) with deterministic tie-breaking."""
        count_stmt = select(func.count(User.id))
        total = (await self.session.execute(count_stmt)).scalar_one() or 0

        if total == 0:
            return [], 0

        stmt = (
            select(
                User.id.label("user_id"),
                User.username.label("username"),
                User.avatar_url.label("avatar_url"),
                func.coalesce(UserStats.rating_elo, DEFAULT_RATING).label("elo"),
            )
            .outerjoin(UserStats, User.id == UserStats.user_id)
            .order_by(
                func.coalesce(UserStats.rating_elo, DEFAULT_RATING).desc(),
                func.coalesce(UserStats.wins, 0).desc(),
                User.id.asc(),
            )
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        items = [
            {
                "rank": offset + idx + 1,
                "user_id": user_id_to_string(row.user_id),
                "username": row.username,
                "avatar_url": row.avatar_url,
                "elo": row.elo,
            }
            for idx, row in enumerate(rows)
        ]

        return items, total

    async def get_words_leaderboard(
        self, limit: int = 20, offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        """Fetch paginated top-scoring words cast in completed matches."""
        count_stmt = (
            select(func.count(MatchCast.id))
            .join(Match, MatchCast.match_id == Match.id)
            .where(Match.status == MatchStatus.FINISHED)
        )
        total = (await self.session.execute(count_stmt)).scalar_one() or 0

        if total == 0:
            return [], 0

        stmt = (
            select(
                MatchCast.id.label("cast_id"),
                MatchCast.word_played.label("word"),
                MatchCast.damage_dealt.label("score"),
                MatchCast.player_id.label("user_id"),
                User.username.label("username"),
                MatchCast.match_id.label("match_id"),
                MatchCast.created_at.label("played_at"),
            )
            .join(Match, MatchCast.match_id == Match.id)
            .join(User, MatchCast.player_id == User.id)
            .where(Match.status == MatchStatus.FINISHED)
            .order_by(
                MatchCast.damage_dealt.desc(),
                MatchCast.created_at.desc(),
                MatchCast.id.asc(),
            )
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        items = [
            {
                "rank": offset + idx + 1,
                "word": row.word,
                "score": row.score,
                "user_id": user_id_to_string(row.user_id),
                "username": row.username,
                "match_id": user_id_to_string(row.match_id),
                "played_at": row.played_at,
            }
            for idx, row in enumerate(rows)
        ]

        return items, total

    async def get_damage_leaderboard(
        self, limit: int = 20, offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        """Fetch paginated players ranked by lifetime total damage dealt across matches."""
        count_stmt = select(func.count(User.id))
        total = (await self.session.execute(count_stmt)).scalar_one() or 0

        if total == 0:
            return [], 0

        stmt = (
            select(
                User.id.label("user_id"),
                User.username.label("username"),
                func.coalesce(UserStats.total_damage_dealt, 0).label("total_damage"),
                func.coalesce(UserStats.matches_played, 0).label("matches_played"),
            )
            .outerjoin(UserStats, User.id == UserStats.user_id)
            .order_by(
                func.coalesce(UserStats.total_damage_dealt, 0).desc(),
                func.coalesce(UserStats.matches_played, 0).desc(),
                User.id.asc(),
            )
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        items = [
            {
                "rank": offset + idx + 1,
                "user_id": user_id_to_string(row.user_id),
                "username": row.username,
                "total_damage": row.total_damage,
                "matches_played": row.matches_played,
            }
            for idx, row in enumerate(rows)
        ]

        return items, total
