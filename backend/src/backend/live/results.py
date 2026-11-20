"""Writing a live match to MySQL: each cast as it happens, the result at the end."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.identifiers import user_id_to_bytes
from backend.game.state import MatchState
from backend.models.match import Match, MatchCast, MatchEndReason, MatchStatus
from backend.models.user_stats import DEFAULT_RATING, UserStats

SessionFactory = Callable[[], AsyncSession]

# Elo: how far one result moves a rating.
ELO_K = 32


def elo_after(rating: int, opponent: int, score: float) -> int:
    """New rating after one game; score is 1 for a win, 0 for a loss."""
    expected = 1 / (1 + 10 ** ((opponent - rating) / 400))
    return round(rating + ELO_K * (score - expected))


async def save_cast(
    session_factory: SessionFactory, state: MatchState, resolved: dict[str, Any]
) -> None:
    """Record one WORD_RESOLVED payload as a match_casts row."""
    totals = resolved["totals"]
    async with session_factory() as session:
        session.add(
            MatchCast(
                match_id=user_id_to_bytes(state.match_id),
                turn_number=resolved["turn"],
                player_id=user_id_to_bytes(resolved["player_id"]),
                word_played=resolved["word"][:32],
                damage_dealt=totals["damage"],
                defense_gained=totals["defense"],
                heal_amount=totals["heal"],
                status_effects_applied={"statuses": resolved["statuses_applied"]},
                glyphs_payload={"steps": resolved["steps"]},
            )
        )
        await session.commit()


async def _stats(session: AsyncSession, user_id: bytes) -> UserStats:
    stats = await session.get(UserStats, user_id)
    if stats is None:
        stats = UserStats(user_id=user_id, rating_elo=DEFAULT_RATING)
        session.add(stats)
        await session.flush()
    return stats


async def save_result(
    session_factory: SessionFactory, state: MatchState
) -> dict[str, int]:
    """Finish the match row and both players' stats. Returns each player's
    Elo change by user id. Does nothing (returns {}) if already saved."""
    assert state.winner is not None and state.end_reason is not None
    match_id = user_id_to_bytes(state.match_id)
    async with session_factory() as session:
        match = await session.get(Match, match_id)
        if match is None or match.status != MatchStatus.ACTIVE:
            return {}

        players = [user_id_to_bytes(p.user_id) for p in state.players]
        stats = [await _stats(session, player) for player in players]
        before = [s.rating_elo for s in stats]
        after = [
            elo_after(before[i], before[1 - i], 1.0 if state.winner == i else 0.0)
            for i in (0, 1)
        ]

        now = datetime.now(UTC).replace(tzinfo=None)
        match.status = MatchStatus.FINISHED
        match.winner_id = players[state.winner]
        match.end_reason = MatchEndReason(state.end_reason.value)
        match.player1_final_hp = state.players[0].hp
        match.player2_final_hp = state.players[1].hp
        match.total_turns = state.turn
        match.ended_at = now
        if match.started_at is not None:
            match.duration_seconds = max(
                0, int((now - match.started_at).total_seconds())
            )
        match.player1_elo_before, match.player2_elo_before = before
        match.player1_elo_after, match.player2_elo_after = after

        casts = (
            await session.execute(
                select(
                    MatchCast.player_id,
                    func.coalesce(func.sum(MatchCast.damage_dealt), 0),
                )
                .where(MatchCast.match_id == match_id)
                .group_by(MatchCast.player_id)
            )
        ).all()
        damage = {player: int(total) for player, total in casts}
        best = {
            cast.player_id: cast
            for cast in (
                await session.scalars(
                    select(MatchCast)
                    .where(MatchCast.match_id == match_id)
                    .order_by(MatchCast.damage_dealt)
                )
            ).all()
        }  # the last one per player is their highest-damage word

        for i, row in enumerate(stats):
            row.matches_played += 1
            row.wins += int(state.winner == i)
            row.losses += int(state.winner != i)
            row.rating_elo = after[i]
            row.total_damage_dealt += damage.get(players[i], 0)
            top = best.get(players[i])
            if top is not None and top.damage_dealt > row.highest_word_score:
                row.highest_word_score = top.damage_dealt
                row.highest_scoring_word = top.word_played
        await session.commit()

    return {p.user_id: after[i] - before[i] for i, p in enumerate(state.players)}
