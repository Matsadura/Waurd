"""The match rows in MySQL: who sits where, saving results, abandoning, and
the achievements a result moves forward."""

import uuid
from dataclasses import asdict
from datetime import UTC, datetime

from backend.core.identifiers import user_id_to_bytes, user_id_to_string
from backend.core.matchmaking_store import MatchmakingQueueStore
from backend.db.session import async_session_maker
from backend.game.achievements import ACHIEVEMENTS
from backend.game.calculations import XP_PER_LOSS, XP_PER_WIN, add_xp, new_elo_ratings
from backend.game.models import Match
from backend.game.perks.catalog import CATALOG
from backend.game.perks.effects import KIND
from backend.game.rules import attack_of
from backend.models.match import Match as MatchRecord
from backend.models.achievements import Achievement
from backend.models.match import MatchCast, MatchStatus
from backend.models.perk import ModificationType, Perk, Rarity, TargetGlyphType
from backend.models.user_achievements import UserAchievement
from backend.models.user_loadout import UserLoadout
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
    """Wins, losses, streaks, damage, best word and heal, Elo and XP for both
    players, plus the Elo history."""
    stats = UserStatsRepository(db)
    p1 = await stats.get_by_id(record.player1_id)
    p2 = await stats.get_by_id(record.player2_id)

    user_repo = UserRepository(db)
    user1 = await user_repo.get_by_id(record.player1_id)
    user2 = await user_repo.get_by_id(record.player2_id)

    record.player1_elo_before = p1.rating_elo
    record.player2_elo_before = p2.rating_elo

    winner, loser = (p1, p2) if record.winner_id == record.player1_id else (p2, p1)
    winner.win_streak += 1
    winner.best_win_streak = max(winner.best_win_streak, winner.win_streak)
    loser.win_streak = 0

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

    # Damage is the HP each cast took (heals can win HP back, so the final HP
    # alone undercounts). A word's score is its full glyph value, even past
    # the opponent's last HP.
    for cast in match.casts:
        player = (p1, p2)[cast.player_index]
        player.total_damage_dealt += cast.damage
        player.highest_heal = max(player.highest_heal, cast.healed)
        score = attack_of(cast.glyphs)
        if score > player.highest_word_score:
            player.highest_word_score = score
            player.highest_scoring_word = cast.word

    record.player1_elo_after = p1.rating_elo
    record.player2_elo_after = p2.rating_elo


async def match_setup(
    match_id: str,
) -> tuple[int, tuple[str, str], tuple[list[str], list[str]]]:
    """Seconds on each player's clock, the players' names for the log, and the
    perks each has equipped (they start the match in hand)."""
    async with async_session_maker() as db:
        record = await MatchRepository(db).get_match_by_id(uuid.UUID(match_id).bytes)
        users = UserRepository(db)
        player1 = await users.get_by_id(record.player1_id)
        player2 = await users.get_by_id(record.player2_id)
        loadouts = []
        for player_id in (record.player1_id, record.player2_id):
            equipped = await db.scalars(
                select(UserLoadout.perk_id).where(UserLoadout.user_id == player_id)
            )
            loadouts.append([p for p in equipped if p in CATALOG])
    names = (player1.username, player2.username)
    return record.time_control_seconds, names, (loadouts[0], loadouts[1])


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
            heal_amount=cast.healed,
            defense_gained=cast.defense,
            # effect -> turns, e.g. {"weak": 2}; None when the word put none on
            status_effects_applied=cast.statuses or None,
            glyphs_payload={"glyphs": [asdict(glyph) for glyph in cast.glyphs]},
            created_at=cast.cast_at,
        )
        for cast in match.casts
    ]


async def save_result(app: FastAPI, match_id: str, match: Match) -> None:
    """Write the result to MySQL, then let both players queue again.

    The result is committed on its own first, so a failure in the stats, cast
    history or achievement steps can't leave the match ACTIVE and the players
    unable to queue."""
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
        async with async_session_maker() as db:
            for player_id in player_ids:
                await record_achievements(db, player_id)
            await db.commit()
    finally:
        queue_store = MatchmakingQueueStore(app.state.redis)
        for player_id in player_ids:
            await queue_store.clear_matched_ticket(user_id_to_string(player_id))


async def record_achievements(db: AsyncSession, user_id: bytes) -> None:
    """Move the player's achievements forward from their stats. Completing one
    gives its XP, once."""
    stats = await UserStatsRepository(db).get_by_id(user_id)
    user = await UserRepository(db).get_by_id(user_id)
    # every match's casts are saved before this step runs
    words = set(
        await db.scalars(
            select(MatchCast.word_played)
            .where(MatchCast.player_id == user_id)
            .distinct()
        )
    )
    rows = {
        row.achievement_id: row
        for row in await db.scalars(
            select(UserAchievement).where(UserAchievement.user_id == user_id)
        )
    }
    for achievement in ACHIEVEMENTS:
        progress = min(achievement.progress(stats, words), achievement.target_value)
        row = rows.get(achievement.id)
        if progress == 0 or (row is not None and row.is_completed):
            continue
        if row is None:
            row = UserAchievement(user_id=user_id, achievement_id=achievement.id)
            db.add(row)
        row.current_progress = progress
        if progress == achievement.target_value:
            row.is_completed = True
            row.unlocked_at = datetime.now(UTC).replace(tzinfo=None)
            add_xp(user, achievement.xp_reward)


async def sync_perks() -> None:
    """Write catalog.csv into the perks table: add new rows, update changed ones.
    A perk no longer in the CSV is disabled, not deleted (loadouts and
    achievements may point at it)."""
    async with async_session_maker() as db:
        rows = {perk.id: perk for perk in await db.scalars(select(Perk))}
        for spec in CATALOG.values():
            row = rows.pop(spec.id, None)
            if row is None:
                row = Perk(id=spec.id)
                db.add(row)
            row.name = spec.name
            row.description = spec.description
            row.quote = spec.quote
            row.image_url = spec.image
            row.rarity = Rarity(spec.rarity.upper())
            row.target_glyph_type = TargetGlyphType(spec.target.upper())
            row.modification_type = ModificationType(KIND[spec.id])
            row.durability = spec.durability
            row.effect_payload = {"mechanics": spec.mechanics}
            row.is_enabled = spec.ready
        for leftover in rows.values():
            leftover.is_enabled = False
        await db.commit()


async def sync_achievements() -> None:
    """Write the achievements list into the table. An icon set in the database
    is kept."""
    async with async_session_maker() as db:
        for achievement in ACHIEVEMENTS:
            perk = achievement.reward_perk_id
            if perk is not None and await db.get(Perk, perk) is None:
                raise ValueError(
                    f"Achievement {achievement.id} rewards perk {perk!r}, "
                    "which isn't in the perks table."
                )
            row = await db.get(Achievement, achievement.id)
            if row is None:
                row = Achievement(id=achievement.id, icon_url="")
                db.add(row)
            row.name = achievement.name
            row.description = achievement.description
            row.xp_reward = achievement.xp_reward
            row.target_value = achievement.target_value
            row.reward_perk_id = achievement.reward_perk_id
        await db.commit()


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
