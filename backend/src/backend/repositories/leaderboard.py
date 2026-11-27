from typing import Any

from backend.core.identifiers import user_id_to_string
from backend.models.match import Match, MatchCast, MatchStatus
from backend.models.user import User
from backend.models.user_stats import DEFAULT_RATING, UserStats
from backend.repositories.base import BaseRepository
from backend.schemas.leaderboard import LeaderboardFilter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


# filter_by -> (what it ranks on, the tie-break before user id). Players with
# no stats row yet count as new players.
PLAYER_BOARDS = {
    LeaderboardFilter.ELO: (
        func.coalesce(UserStats.rating_elo, DEFAULT_RATING),
        func.coalesce(UserStats.wins, 0),
    ),
    LeaderboardFilter.DAMAGE: (
        func.coalesce(UserStats.total_damage_dealt, 0),
        func.coalesce(UserStats.matches_played, 0),
    ),
    LeaderboardFilter.WIN_STREAK: (
        func.coalesce(UserStats.best_win_streak, 0),
        func.coalesce(UserStats.win_streak, 0),
    ),
    LeaderboardFilter.HEAL: (
        func.coalesce(UserStats.highest_heal, 0),
        func.coalesce(UserStats.wins, 0),
    ),
}


class LeaderboardRepository(BaseRepository[User]):
    """Leaderboard queries: players ranked by one stat, and the best words."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_player_leaderboard(
        self, filter_by: LeaderboardFilter, limit: int = 20, offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        """Every player ranked by one stat (DESC), with deterministic tie-breaking.
        Players without a stats row count as new players."""
        value, tiebreak = PLAYER_BOARDS[filter_by]
        total = (await self.session.execute(select(func.count(User.id)))).scalar_one()
        if total == 0:
            return [], 0

        matches = func.coalesce(UserStats.matches_played, 0)
        stmt = (
            select(
                User.id.label("user_id"),
                User.username.label("username"),
                User.avatar_url.label("avatar_url"),
                value.label("value"),
                matches.label("matches_played"),
            )
            .outerjoin(UserStats, User.id == UserStats.user_id)
            .order_by(value.desc(), tiebreak.desc(), User.id.asc())
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        items = [
            {
                "rank": offset + idx + 1,
                "user_id": user_id_to_string(row.user_id),
                "username": row.username,
                "avatar_url": row.avatar_url,
                "value": row.value,
                "matches_played": row.matches_played,
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
