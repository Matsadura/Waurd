"""The match rows in MySQL: who sits where, saving results, abandoning."""

import uuid
from dataclasses import asdict

from backend.core.identifiers import user_id_to_bytes, user_id_to_string
from backend.core.matchmaking_store import MatchmakingQueueStore
from backend.db.session import async_session_maker
from backend.game.calculations import XP_PER_LOSS, XP_PER_WIN, add_xp, new_elo_ratings
from backend.game.models import Match
from backend.game.rules import STARTING_HP
from backend.models.match import Match as MatchRecord
from backend.models.match import MatchCast, MatchStatus
from backend.repositories.match import MatchRepository
from backend.repositories.user import UserRepository
from backend.repositories.user_stats import UserStatsRepository
from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def seat_in_match(match_id: str, user_id: str) -> int | None:
    """0 if the user is player1 of this active match, 1 if player2, else None."""
    async with async_session_maker() as db:
        record = await MatchRepository(db).get_match_by_id(uuid.UUID(match_id).bytes)
    if record is None or record.status != MatchStatus.ACTIVE:
        return None

    user_id_bytes = user_id_to_bytes(user_id)
    if record.player1_id == user_id_bytes:
        return 0
    if record.player2_id == user_id_bytes:
        return 1
    return None


async def final_result(match_id: str, user_id: str) -> dict | None:
    """The result of a finished match, for a player who reconnects after the end."""
    async with async_session_maker() as db:
        record = await MatchRepository(db).get_match_by_id(uuid.UUID(match_id).bytes)
    if record is None or record.status != MatchStatus.FINISHED:
        return None

    me = user_id_to_bytes(user_id)
    if me == record.player1_id:
        my_hp, their_hp = record.player1_final_hp, record.player2_final_hp
    elif me == record.player2_id:
        my_hp, their_hp = record.player2_final_hp, record.player1_final_hp
    else:
        return None
    return {
        "type": "STATE",
        "turn": record.total_turns,
        "your_turn": False,
        "winner": 0 if record.winner_id == record.player1_id else 1,
        "you_won": record.winner_id == me,
        "end_reason": record.end_reason.value,
        "you": {"hp": my_hp, "hand": []},
        "opponent": {"hp": their_hp, "hand_size": 0},
    }


async def update_stats(db: AsyncSession, record: MatchRecord, match: Match) -> None:
    """Wins, losses, damage, best word, Elo and XP for both players, plus the
    Elo history."""
    stats = UserStatsRepository(db)
    p1 = await stats.get_by_id(record.player1_id)
    p2 = await stats.get_by_id(record.player2_id)

    user_repo = UserRepository(db)
    user1 = await user_repo.get_by_id(record.player1_id)
    user2 = await user_repo.get_by_id(record.player2_id)

    record.player1_elo_before = p1.rating_elo
    record.player2_elo_before = p2.rating_elo

    if record.winner_id == record.player1_id:
        p1.rating_elo, p2.rating_elo = new_elo_ratings(p1.rating_elo, p2.rating_elo)
        p1.wins += 1
        p2.losses += 1
        add_xp(user1, XP_PER_WIN)
        add_xp(user2, XP_PER_LOSS)
    else:
        p2.rating_elo, p1.rating_elo = new_elo_ratings(p2.rating_elo, p1.rating_elo)
        p2.wins += 1
        p1.losses += 1
        add_xp(user2, XP_PER_WIN)
        add_xp(user1, XP_PER_LOSS)

    p1.matches_played += 1
    p2.matches_played += 1
    p1.total_damage_dealt += STARTING_HP - record.player2_final_hp
    p2.total_damage_dealt += STARTING_HP - record.player1_final_hp

    # A word's score is its full glyph value, even past the opponent's last HP.
    for cast in match.casts:
        player = (p1, p2)[cast.player_index]
        score = sum(glyph.damage for glyph in cast.glyphs)
        if score > player.highest_word_score:
            player.highest_word_score = score
            player.highest_scoring_word = cast.word

    record.player1_elo_after = p1.rating_elo
    record.player2_elo_after = p2.rating_elo


async def time_control(match_id: str) -> int:
    """Seconds on each player's clock, as chosen when the match was created."""
    async with async_session_maker() as db:
        record = await MatchRepository(db).get_match_by_id(uuid.UUID(match_id).bytes)
    return record.time_control_seconds


def cast_rows(
    match_id_bytes: bytes, player_ids: tuple[bytes, bytes], match: Match
) -> list[MatchCast]:
    """The match history: one match_casts row per word cast."""
    return [
        MatchCast(
            match_id=match_id_bytes,
            turn_number=cast.turn,
            player_id=player_ids[cast.player_index],
            word_played=cast.word,
            damage_dealt=cast.damage,
            glyphs_payload={"glyphs": [asdict(glyph) for glyph in cast.glyphs]},
            created_at=cast.cast_at,
        )
        for cast in match.casts
    ]


async def save_result(app: FastAPI, match_id: str, match: Match) -> None:
    """Write the result to MySQL, then let both players queue again.

    The result is committed on its own first, so a failure in the stats or
    cast history steps can't leave the match ACTIVE and the players unable
    to queue."""
    match_id_bytes = uuid.UUID(match_id).bytes
    async with async_session_maker() as db:
        record = await MatchRepository(db).finish_match(
            match_id_bytes,
            winner_seat=match.winner,
            player1_hp=match.players[0].hp,
            player2_hp=match.players[1].hp,
            total_turns=match.turn,
            end_reason=match.end_reason,
        )
        time_used = sum(
            record.time_control_seconds - p.time_left for p in match.players
        )
        record.duration_seconds = round(time_used)
        await db.commit()
        player_ids = (record.player1_id, record.player2_id)

    try:
        async with async_session_maker() as db:
            record = await MatchRepository(db).get_match_by_id(match_id_bytes)
            await update_stats(db, record, match)
            await db.commit()
        async with async_session_maker() as db:
            db.add_all(cast_rows(match_id_bytes, player_ids, match))
            await db.commit()
    finally:
        queue_store = MatchmakingQueueStore(app.state.redis)
        for player_id in player_ids:
            await queue_store.clear_matched_ticket(user_id_to_string(player_id))


async def abandon(app: FastAPI, match_id: str) -> None:
    """End a match with no winner and let both players queue again."""
    async with async_session_maker() as db:
        record = await MatchRepository(db).get_match_by_id(uuid.UUID(match_id).bytes)
        player_ids = (record.player1_id, record.player2_id)
        if record.status == MatchStatus.ACTIVE:
            record.status = MatchStatus.ABANDONED
            record.ended_at = func.now()
            await db.commit()

    queue_store = MatchmakingQueueStore(app.state.redis)
    for player_id in player_ids:
        await queue_store.clear_matched_ticket(user_id_to_string(player_id))


async def abandon_unfinished_matches(app: FastAPI) -> None:
    """Games live in memory, so a restart loses them: free their players."""
    async with async_session_maker() as db:
        ids = (
            await db.scalars(
                select(MatchRecord.id).where(MatchRecord.status == MatchStatus.ACTIVE)
            )
        ).all()
    for match_id in ids:
        await abandon(app, str(uuid.UUID(bytes=match_id)))
