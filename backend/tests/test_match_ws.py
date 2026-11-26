"""The match WebSocket and its database side (match_ws.py, records.py): saving
results, sending, bad messages, arrival, ids, abandoning, the result after the
end, who starts, the clock and the cast history."""

import json
import time
import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest

match_ws = pytest.importorskip(
    "backend.ws.match_ws", reason="The match socket is not merged yet"
)
records = pytest.importorskip(
    "backend.ws.records", reason="The match socket is not merged yet"
)

from backend.game.rules import (
    SECOND_PLAYER_SHIELD,
    cast_word,
    lose_by_disconnect,
    pass_turn,
    resign,
    start_turn,
    use_time,
)
from backend.game.models import Cast, Glyph
from backend.game.setup import new_match
from fastapi import WebSocketDisconnect
from starlette.testclient import TestClient

from backend.main import app
from sqlalchemy import select
from backend.models import (
    Achievement,
    Match,
    MatchStatus,
    User,
    UserAchievement,
    UserStats,
)

ORIGIN = "http://localhost:5173"


@pytest.fixture(autouse=True)
def fresh_state(monkeypatch, session_maker):  # type: ignore[no-untyped-def]
    match_ws.matches.clear()
    match_ws.sockets.clear()
    match_ws.timers.clear()
    match_ws.clocks.clear()
    monkeypatch.setattr(records, "async_session_maker", session_maker)
    yield
    for task in [*match_ws.timers.values(), *match_ws.clocks.values()]:
        task.cancel()


@pytest.fixture(autouse=True)
async def achievements(fresh_state):  # type: ignore[no-untyped-def]
    """The startup step that fills the achievements table."""
    await records.sync_achievements()


async def active_match(session_maker, alice, bob, stats=True) -> str:  # type: ignore[no-untyped-def]
    match_id = uuid.uuid4()
    async with session_maker() as db:
        # Registration gives every user a stats row.
        for user in (alice, bob) if stats else ():
            db.add(
                UserStats(
                    user_id=user.id,
                    matches_played=0,
                    wins=0,
                    losses=0,
                    rating_elo=1200,
                    total_damage_dealt=0,
                )
            )
        db.add(
            Match(
                id=match_id.bytes,
                player1_id=alice.id,
                player2_id=bob.id,
                time_control_seconds=180,
                status=MatchStatus.ACTIVE,
            )
        )
        await db.commit()
    return str(match_id)


def finished_game():  # type: ignore[no-untyped-def]
    game = new_match(seed=1)
    game.players[1].hp = 40
    game.turn = 5
    resign(game, 1)  # player 0 wins
    return game


def fake_app(redis):  # type: ignore[no-untyped-def]
    return SimpleNamespace(state=SimpleNamespace(redis=redis))


class TestSavingTheResult:
    async def test_result_updates_both_players_stats(
        self, session_maker, redis, alice, bob
    ) -> None:
        match_id = await active_match(session_maker, alice, bob)

        await records.save_result(fake_app(redis), match_id, finished_game())

        async with session_maker() as db:
            winner = await db.get(UserStats, alice.id)
            loser = await db.get(UserStats, bob.id)
            record = await db.get(Match, uuid.UUID(match_id).bytes)
        assert (winner.wins, winner.matches_played, winner.rating_elo) == (1, 1, 1216)
        assert (loser.losses, loser.matches_played, loser.rating_elo) == (1, 1, 1184)
        assert winner.total_damage_dealt == 60
        assert record.status == MatchStatus.FINISHED
        assert (record.player1_elo_before, record.player1_elo_after) == (1200, 1216)

    async def test_result_is_kept_when_the_stats_step_fails(
        self, session_maker, redis, alice, bob, monkeypatch
    ) -> None:
        match_id = await active_match(session_maker, alice, bob)
        for user in (alice, bob):
            await redis.set(
                f"matchmaking:user:{uuid.UUID(bytes=user.id)}",
                json.dumps({"status": "MATCHED"}),
            )

        async def broken(db, record, match):  # type: ignore[no-untyped-def]
            raise RuntimeError("stats exploded")

        monkeypatch.setattr(records, "update_stats", broken)
        match_ws.matches[match_id] = finished_game()

        await match_ws.end_match(fake_app(redis), match_id, match_ws.matches[match_id])

        async with session_maker() as db:
            record = await db.get(Match, uuid.UUID(match_id).bytes)
        assert record.status == MatchStatus.FINISHED  # not stuck ACTIVE
        assert record.winner_id == alice.id
        for user in (alice, bob):  # both can queue again
            assert (
                await redis.get(f"matchmaking:user:{uuid.UUID(bytes=user.id)}") is None
            )
        assert match_id not in match_ws.matches


class TestEnding:
    async def test_abandon_while_playing_is_a_resignation(
        self, session_maker, alice, bob, alice_client
    ) -> None:
        match_id = await active_match(session_maker, alice, bob)
        game = new_match(seed=1)
        use_time(game, time.monotonic())  # the clock starts with the game, as in play()
        start_turn(game)
        match_ws.matches[match_id] = game
        bob_socket = LiveSocket()
        match_ws.sockets[match_id] = {1: bob_socket}

        response = await alice_client.delete(f"/matchmaking/matches/{match_id}/abandon")

        assert response.status_code == 200
        async with session_maker() as db:
            record = await db.get(Match, uuid.UUID(match_id).bytes)
        assert record.status == MatchStatus.FINISHED
        assert record.winner_id == bob.id
        assert bob_socket.messages[-1]["you_won"] is True  # bob is told
        assert match_id not in match_ws.matches

    async def test_a_restart_abandons_active_matches(
        self, session_maker, redis, alice, bob
    ) -> None:
        match_id = await active_match(session_maker, alice, bob)
        await redis.set(
            f"matchmaking:user:{uuid.UUID(bytes=alice.id)}",
            json.dumps({"status": "MATCHED"}),
        )

        await records.abandon_unfinished_matches(fake_app(redis))

        async with session_maker() as db:
            record = await db.get(Match, uuid.UUID(match_id).bytes)
        assert record.status == MatchStatus.ABANDONED
        assert record.ended_at is not None
        assert await redis.get(f"matchmaking:user:{uuid.UUID(bytes=alice.id)}") is None

    async def test_a_finished_match_shows_its_result(
        self, session_maker, redis, alice, bob
    ) -> None:
        match_id = await active_match(session_maker, alice, bob)
        await records.save_result(fake_app(redis), match_id, finished_game())

        loser = await records.final_result(match_id, str(uuid.UUID(bytes=bob.id)))

        assert loser["winner"] == 0
        assert loser["you_won"] is False
        assert loser["end_reason"] == "RESIGNATION"
        assert (loser["you"]["hp"], loser["opponent"]["hp"]) == (40, 100)

    async def test_an_active_match_has_no_final_result(
        self, session_maker, alice, bob
    ) -> None:
        match_id = await active_match(session_maker, alice, bob)

        assert (
            await records.final_result(match_id, str(uuid.UUID(bytes=bob.id))) is None
        )


class TestLeavingBeforeTheStart:
    @pytest.fixture(autouse=True)
    def quick(self, monkeypatch):  # type: ignore[no-untyped-def]
        monkeypatch.setattr(match_ws, "GRACE_SECONDS", 0.01)
        self.ended: list[tuple[int, str]] = []
        self.abandoned: list[str] = []

        async def end(app, match_id, game):  # type: ignore[no-untyped-def]
            self.ended.append((game.winner, game.end_reason))

        async def abandon(app, match_id):  # type: ignore[no-untyped-def]
            self.abandoned.append(match_id)

        monkeypatch.setattr(match_ws, "end_match", end)
        monkeypatch.setattr(match_ws, "abandon", abandon)

    async def test_leaving_before_the_start_aborts_even_if_the_other_arrived(
        self,
    ) -> None:
        match_ws.matches["m"] = new_match(seed=1)
        socket = LiveSocket()
        socket.app = None  # type: ignore[attr-defined]
        match_ws.sockets["m"] = {0: socket}

        await match_ws.left(socket, "m", 0)
        waiting = LiveSocket()
        match_ws.sockets["m"] = {1: waiting}  # the opponent arrives, alone
        await match_ws.timers[("m", 0)]

        assert self.abandoned == ["m"]
        assert self.ended == []  # no winner: no rating or XP change
        assert waiting.messages == [{"type": "MATCH_ABORTED"}]
        assert waiting.closed

    async def test_nobody_there_abandons_the_match(self) -> None:
        match_ws.matches["m"] = new_match(seed=1)
        socket = LiveSocket()
        socket.app = None  # type: ignore[attr-defined]
        match_ws.sockets["m"] = {0: socket}

        await match_ws.left(socket, "m", 0)
        await match_ws.timers[("m", 0)]

        assert self.abandoned == ["m"]
        assert self.ended == []


class TestRules:
    def test_either_player_can_start(self) -> None:
        starters = {new_match(seed=seed).active_player_index for seed in range(20)}

        assert starters == {0, 1}

    def test_booleans_are_not_positions(self) -> None:
        game = new_match(seed=1)
        start_turn(game)

        with pytest.raises(ValueError):
            cast_word(game, game.active_player_index, [True, False], {"ab"})

    def test_a_glyph_is_shown_with_its_type_and_effect(self) -> None:
        game = new_match(seed=1)
        start_turn(game)
        me = game.active_player_index

        glyph = match_ws.view(game, me)["you"]["hand"][0]

        assert glyph == {
            "position": 0,
            "letter": game.players[me].hand[0].letter,
            "type": "power",
            "effect_type": "damage",
            "effect_value": game.players[me].hand[0].effect_value,
        }

    def test_the_state_shows_my_piles_and_only_counts_for_the_opponent(self) -> None:
        game = new_match(seed=1)
        start_turn(game)
        me = game.active_player_index
        pass_turn(game, me)  # my hand goes to my discard pile
        player, opponent = game.players[me], game.players[1 - me]

        state = match_ws.view(game, me)

        assert [g["letter"] for g in state["you"]["discard_pile"]] == [
            g.letter for g in player.discard_pile
        ]
        assert len(player.discard_pile) == 12
        # the draw pile is sorted, so it doesn't give the next draws away
        assert [g["letter"] for g in state["you"]["draw_pile"]] == sorted(
            g.letter for g in player.draw_pile
        )
        assert state["opponent"] == {
            "hp": opponent.hp,
            "hand_size": len(opponent.hand),
            "draw_pile_size": len(opponent.draw_pile),
            "discard_pile_size": 0,
            "defense": 0,
            "statuses": {},
        }
        assert "draw_pile" not in state["opponent"]

    def test_only_damage_effects_hurt(self) -> None:
        game = new_match(seed=1)
        game.active_player_index = 0
        start_turn(game)
        game.players[0].hand = [
            Glyph("A", 6),
            Glyph("T", 30, type="power", effect_type="heal"),
        ]

        cast_word(game, 0, [0, 1], {"AT"})

        assert game.players[1].hp == 94

    def test_the_state_says_who_won(self) -> None:
        game = finished_game()

        assert match_ws.view(game, 0)["you_won"] is True
        assert match_ws.view(game, 1)["you_won"] is False
        assert match_ws.view(game, 1)["end_reason"] == "RESIGNATION"
        assert match_ws.view(new_match(seed=1), 0)["you_won"] is None


class TestClock:
    def started(self, seconds: int = 300):  # type: ignore[no-untyped-def]
        game = new_match(seed=1, time_control_seconds=seconds)
        use_time(game, 0.0)
        start_turn(game)
        return game

    def test_each_player_gets_the_whole_time_control(self) -> None:
        game = new_match(seed=1, time_control_seconds=300)

        assert [player.time_left for player in game.players] == [300, 300]

    def test_only_the_active_players_clock_runs(self) -> None:
        game = self.started()
        first = game.active_player_index

        use_time(game, 20.0)

        assert game.players[first].time_left == 280
        assert game.players[1 - first].time_left == 300

    def test_a_long_turn_does_not_pass_on_its_own(self) -> None:
        game = self.started()

        use_time(game, 100.0)

        assert (game.turn, game.winner) == (1, None)

    def test_running_out_of_time_loses(self) -> None:
        game = self.started(seconds=10)
        first = game.active_player_index

        use_time(game, 10.0)

        assert (game.winner, game.end_reason) == (1 - first, "TIMEOUT")

    async def test_the_clock_ends_the_match_and_stops(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        async def no_database(app, match_id, game):  # type: ignore[no-untyped-def]
            pass

        monkeypatch.setattr(match_ws, "save_result", no_database)
        game = new_match(seed=1, time_control_seconds=300)
        use_time(game, time.monotonic())
        start_turn(game)
        game.players[game.active_player_index].time_left = 0.05
        match_ws.matches["m"] = game
        watcher = LiveSocket()
        match_ws.sockets["m"] = {1 - game.active_player_index: watcher}

        match_ws.restart_clock(None, "m", game)  # type: ignore[arg-type]
        await match_ws.clocks["m"]

        assert game.end_reason == "TIMEOUT"
        assert watcher.messages[-1]["you_won"] is True
        assert "m" not in match_ws.matches
        assert "m" not in match_ws.clocks  # nothing left ticking

    async def test_the_duration_is_the_time_both_players_used(
        self, session_maker, redis, alice, bob
    ) -> None:
        match_id = await active_match(session_maker, alice, bob)  # 180 seconds
        game = finished_game()
        game.players[0].time_left, game.players[1].time_left = 150, 170  # of 180 each

        await records.save_result(fake_app(redis), match_id, game)

        async with session_maker() as db:
            record = await db.get(Match, uuid.UUID(match_id).bytes)
        assert record.duration_seconds == 40


def game_with_casts():  # type: ignore[no-untyped-def]
    """Player 0 casts CAT (26), player 1 casts AT (14), then CAT finishes player 1."""
    words = {"CAT", "AT"}
    game = new_match(seed=1, time_control_seconds=300)
    game.active_player_index = 0
    start_turn(game)
    game.players[0].hand = [Glyph("C", 12), Glyph("A", 6), Glyph("T", 8)]
    cast_word(game, 0, [0, 1, 2], words)
    game.players[1].hand = [Glyph("A", 6), Glyph("T", 8)]
    cast_word(game, 1, [0, 1], words)
    game.players[0].hand = [Glyph("C", 40), Glyph("A", 40), Glyph("T", 40)]
    cast_word(game, 0, [0, 1, 2], words)  # 120 damage against 74 HP left
    for minute, cast in enumerate(game.casts):
        cast.cast_at = datetime(2026, 1, 1, 12, minute)
    return game


class TestCastHistory:
    def test_a_cast_records_the_hp_actually_removed(self) -> None:
        game = game_with_casts()

        assert [cast.damage for cast in game.casts] == [26, 14, 74]
        assert game.players[1].hp == 0
        assert game.winner == 0

    async def test_casts_are_saved_in_order(
        self, session_maker, redis, alice, bob, alice_client
    ) -> None:
        match_id = await active_match(session_maker, alice, bob)

        await records.save_result(fake_app(redis), match_id, game_with_casts())

        casts = (
            await alice_client.get(f"/matchmaking/matches/{match_id}/casts")
        ).json()
        alice_id, bob_id = (str(uuid.UUID(bytes=u.id)) for u in (alice, bob))
        assert [
            (c["turn_number"], c["player_id"], c["word_played"], c["damage_dealt"])
            for c in casts
        ] == [(1, alice_id, "CAT", 26), (2, bob_id, "AT", 14), (3, alice_id, "CAT", 74)]
        assert casts[1]["glyphs_payload"] == {
            "glyphs": [
                {
                    "letter": "A",
                    "effect_value": 6,
                    "type": "power",
                    "effect_type": "damage",
                },
                {
                    "letter": "T",
                    "effect_value": 8,
                    "type": "power",
                    "effect_type": "damage",
                },
            ]
        }
        assert [c["created_at"][:16] for c in casts] == [
            "2026-01-01T12:00",
            "2026-01-01T12:01",
            "2026-01-01T12:02",
        ]

    async def test_each_players_best_word_is_recorded(
        self, session_maker, redis, alice, bob
    ) -> None:
        match_id = await active_match(session_maker, alice, bob)

        await records.save_result(fake_app(redis), match_id, game_with_casts())

        async with session_maker() as db:
            alice_stats = await db.get(UserStats, alice.id)
            bob_stats = await db.get(UserStats, bob.id)
        # the finishing CAT counts its full 120, not the 74 HP it removed
        assert (alice_stats.highest_scoring_word, alice_stats.highest_word_score) == (
            "CAT",
            120,
        )
        assert (bob_stats.highest_scoring_word, bob_stats.highest_word_score) == (
            "AT",
            14,
        )

    async def test_a_better_earlier_word_is_kept(
        self, session_maker, redis, alice, bob
    ) -> None:
        match_id = await active_match(session_maker, alice, bob)
        async with session_maker() as db:
            stats = await db.get(UserStats, bob.id)
            stats.highest_scoring_word, stats.highest_word_score = "QUIZ", 90
            await db.commit()

        await records.save_result(fake_app(redis), match_id, game_with_casts())

        async with session_maker() as db:
            stats = await db.get(UserStats, bob.id)
        assert (stats.highest_scoring_word, stats.highest_word_score) == ("QUIZ", 90)

    async def test_a_failed_cast_insert_keeps_the_result(
        self, session_maker, redis, alice, bob, monkeypatch
    ) -> None:
        match_id = await active_match(session_maker, alice, bob)
        for user in (alice, bob):
            await redis.set(
                f"matchmaking:user:{uuid.UUID(bytes=user.id)}",
                json.dumps({"status": "MATCHED"}),
            )
        real_rows = records.cast_rows

        def refused_rows(*args):  # type: ignore[no-untyped-def]
            rows = real_rows(*args)
            rows[0].word_played = None  # a row the database refuses
            return rows

        monkeypatch.setattr(records, "cast_rows", refused_rows)
        game = game_with_casts()
        match_ws.matches[match_id] = game

        await match_ws.end_match(fake_app(redis), match_id, game)

        async with session_maker() as db:
            record = await db.get(Match, uuid.UUID(match_id).bytes)
            winner = await db.get(UserStats, alice.id)
        assert record.status == MatchStatus.FINISHED
        assert record.winner_id == alice.id
        assert winner.wins == 1  # stats are saved before the casts
        for user in (alice, bob):  # both can queue again
            assert (
                await redis.get(f"matchmaking:user:{uuid.UUID(bytes=user.id)}") is None
            )


def named_game():  # type: ignore[no-untyped-def]
    game = new_match(seed=1, time_control_seconds=300)
    game.names = ("alice", "bob")
    game.active_player_index = 0
    use_time(game, 0.0)
    start_turn(game)
    return game


def effects_game():  # type: ignore[no-untyped-def]
    """Player 0 to move on turn 1, with empty hands to fill in each test."""
    game = new_match(seed=1)
    game.names = ("alice", "bob")
    game.active_player_index = 0
    start_turn(game)
    game.players[0].hand = []
    return game


def hit(value):  # type: ignore[no-untyped-def]
    return Glyph("T", value)


class TestEffects:
    def test_heal_restores_the_caster_up_to_full_hp(self) -> None:
        game = effects_game()
        game.players[0].hp = 95
        game.players[0].hand = [Glyph("A", 9, "power", "heal"), hit(4)]

        cast_word(game, 0, [0, 1], {"AT"})

        assert game.players[0].hp == 100
        assert game.players[1].hp == 96
        assert game.log[-1] == "alice cast AT for 4 damage, healed 5"

    def test_defense_blocks_damage_before_hp(self) -> None:
        game = effects_game()
        game.players[0].hand = [Glyph("O", 9, "power", "defense"), Glyph("N", 1)]
        cast_word(game, 0, [0, 1], {"ON"})
        assert game.players[0].defense == 9

        game.players[1].hand = [hit(12)]
        cast_word(game, 1, [0], {"T"})

        assert game.players[0].defense == 0
        assert game.players[0].hp == 97
        assert game.log[-1] == "bob cast T for 3 damage (9 blocked)"

    def test_defense_lasts_until_the_owners_next_turn(self) -> None:
        game = effects_game()
        game.players[0].hand = [Glyph("O", 9, "power", "defense")]
        cast_word(game, 0, [0], {"O"})

        pass_turn(game, 1)

        assert game.players[0].defense == 0

    def test_vulnerable_adds_half_to_later_damage(self) -> None:
        game = effects_game()
        game.players[0].hand = [Glyph("V", 2, "skill", "vulnerable"), hit(10)]
        cast_word(game, 0, [0, 1], {"VT"})
        # the status starts after the word that put it on
        assert game.players[1].hp == 90
        assert (
            game.log[-1] == "alice cast VT for 10 damage, bob is vulnerable for 2 turns"
        )

        pass_turn(game, 1)
        game.players[0].hand = [hit(10), hit(5)]
        cast_word(game, 0, [0, 1], {"TT"})

        assert game.players[1].hp == 90 - 15 - 7  # 5 * 1.5 rounds down

    def test_weak_lowers_every_power_glyph_by_a_quarter(self) -> None:
        game = effects_game()
        game.players[0].hp = 50
        game.players[0].statuses = {"weak": 1}
        game.players[0].hand = [
            hit(10),
            Glyph("A", 10, "power", "heal"),
            Glyph("O", 10, "power", "defense"),
            Glyph("V", 2, "skill", "vulnerable"),
        ]

        cast_word(game, 0, [0, 1, 2, 3], {"TAOV"})

        assert game.players[1].hp == 93
        assert game.players[0].hp == 57
        assert game.players[0].defense == 7
        assert game.players[1].statuses == {"vulnerable": 2}  # durations stay whole

    def test_a_status_counts_down_at_the_end_of_its_owners_turns(self) -> None:
        game = effects_game()
        game.players[0].hand = [Glyph("E", 2, "skill", "weak")]
        cast_word(game, 0, [0], {"E"})
        assert game.players[1].statuses == {"weak": 2}

        pass_turn(game, 1)
        assert game.players[1].statuses == {"weak": 1}
        pass_turn(game, 0)  # only bob's own turns count
        assert game.players[1].statuses == {"weak": 1}
        pass_turn(game, 1)
        assert game.players[1].statuses == {}

    def test_a_status_already_there_keeps_the_longer_time(self) -> None:
        game = effects_game()
        game.players[1].statuses = {"weak": 3}
        game.players[0].hand = [Glyph("E", 2, "skill", "weak")]

        cast_word(game, 0, [0], {"E"})

        assert game.players[1].statuses == {"weak": 3}

    def test_the_state_shows_defense_and_statuses_for_both_players(self) -> None:
        game = effects_game()
        game.players[0].hand = [
            Glyph("O", 9, "power", "defense"),
            Glyph("E", 2, "skill", "weak"),
        ]
        cast_word(game, 0, [0, 1], {"OE"})

        mine, theirs = match_ws.view(game, 0), match_ws.view(game, 1)

        assert (mine["you"]["defense"], mine["opponent"]["statuses"]) == (
            9,
            {"weak": 2},
        )
        assert (theirs["opponent"]["defense"], theirs["you"]["statuses"]) == (
            9,
            {"weak": 2},
        )

    def test_the_second_player_starts_with_defense_until_their_turn(self) -> None:
        game = new_match(seed=1)
        start_turn(game)
        first = game.active_player_index

        assert game.players[first].defense == 0
        assert game.players[1 - first].defense == SECOND_PLAYER_SHIELD
        pass_turn(game, first)
        assert game.players[1 - first].defense == 0

    def test_the_deck_has_every_effect(self) -> None:
        deck = new_match(seed=1).players[0].draw_pile

        assert {(g.type, g.effect_type) for g in deck} == {
            ("power", "damage"),
            ("power", "heal"),
            ("power", "defense"),
            ("skill", "vulnerable"),
            ("skill", "weak"),
        }


class TestMatchLog:
    def test_the_log_tells_each_move_and_the_winner(self) -> None:
        game = named_game()
        pass_turn(game, 0)
        game.players[1].hand = [Glyph("C", 50), Glyph("A", 30), Glyph("T", 40)]
        cast_word(game, 1, [0, 1, 2], {"CAT"})

        assert game.log == [
            "alice goes first",
            "alice passed",
            "bob cast CAT for 100 damage",
            "alice has no HP left. bob wins!",
        ]

    def test_each_way_of_losing_is_explained(self) -> None:
        resigned, left, timed_out = named_game(), named_game(), named_game()
        resign(resigned, 1)
        lose_by_disconnect(left, 0)
        use_time(timed_out, 300.0)

        assert resigned.log[-1] == "bob resigned. alice wins!"
        assert left.log[-1] == "alice didn't come back in time. bob wins!"
        assert timed_out.log[-1] == "alice ran out of time. bob wins!"

    def test_the_state_carries_the_log(self) -> None:
        game = named_game()

        assert match_ws.view(game, 1)["log"] == ["alice goes first"]

    async def test_a_disconnect_is_logged_for_the_other_player(self) -> None:
        match_ws.matches["m"] = game = named_game()
        leaving, staying = LiveSocket(), LiveSocket()
        leaving.app = None  # type: ignore[attr-defined]
        match_ws.sockets["m"] = {0: leaving, 1: staying}

        await match_ws.left(leaving, "m", 0)

        assert staying.messages[0]["type"] == "OPPONENT_DISCONNECTED"
        assert staying.messages[1]["log"][-1] == "alice disconnected"
        assert game.log[-1] == "alice disconnected"


class TestAchievements:
    async def progress(self, session_maker, user) -> dict:  # type: ignore[no-untyped-def]
        """achievement id -> (current_progress, is_completed)"""
        async with session_maker() as db:
            rows = await db.scalars(
                select(UserAchievement).where(UserAchievement.user_id == user.id)
            )
            return {
                r.achievement_id: (r.current_progress, r.is_completed) for r in rows
            }

    async def xp(self, session_maker, user) -> int:  # type: ignore[no-untyped-def]
        async with session_maker() as db:
            return (await db.get(User, user.id)).xp

    async def test_a_won_match_moves_both_players_forward(
        self, session_maker, redis, alice, bob
    ) -> None:
        match_id = await active_match(session_maker, alice, bob)

        await records.save_result(fake_app(redis), match_id, finished_game())

        assert await self.progress(session_maker, alice) == {
            "first-match": (1, True),
            "first-win": (1, True),
            "ten-wins": (1, False),
            "heavy-hitter": (60, False),  # bob ended on 40 HP
        }
        assert await self.progress(session_maker, bob) == {"first-match": (1, True)}
        # match XP plus each completed achievement's reward
        assert await self.xp(session_maker, alice) == 50 + 50 + 100
        assert await self.xp(session_maker, bob) == 20 + 50

    async def test_a_completed_achievement_gives_its_xp_once(
        self, session_maker, redis, alice, bob
    ) -> None:
        for first in (True, False):
            match_id = await active_match(session_maker, alice, bob, stats=first)
            await records.save_result(fake_app(redis), match_id, finished_game())

        assert (await self.progress(session_maker, alice))["ten-wins"] == (2, False)
        assert await self.xp(session_maker, alice) == 2 * 50 + 50 + 100

    async def test_unlocked_at_is_when_it_was_completed(
        self, session_maker, redis, alice, bob
    ) -> None:
        match_id = await active_match(session_maker, alice, bob)
        async with session_maker() as db:  # started long ago, not completed
            db.add(
                UserAchievement(
                    user_id=alice.id,
                    achievement_id="first-win",
                    current_progress=0,
                    unlocked_at=datetime(2000, 1, 1),
                )
            )
            await db.commit()

        await records.save_result(fake_app(redis), match_id, finished_game())

        async with session_maker() as db:
            row = await db.get(UserAchievement, (alice.id, "first-win"))
        assert row.is_completed and row.unlocked_at.year > 2000

    async def test_wordsmith_counts_the_words_full_value(
        self, session_maker, redis, alice, bob
    ) -> None:
        match_id = await active_match(session_maker, alice, bob)

        await records.save_result(fake_app(redis), match_id, game_with_casts())

        # the finishing CAT is worth 120 though it removed only 74 HP
        assert (await self.progress(session_maker, alice))["wordsmith"] == (100, True)

    async def test_progress_is_listed_for_the_player(
        self, session_maker, redis, alice, bob, alice_client
    ) -> None:
        match_id = await active_match(session_maker, alice, bob)
        await records.save_result(fake_app(redis), match_id, finished_game())

        listed = (await alice_client.get("/users/me/achievements")).json()

        mine = {a["achievement_id"]: a for a in listed}
        assert mine["first-win"]["is_completed"] is True
        assert mine["first-win"]["unlocked_at"] is not None
        assert mine["heavy-hitter"]["progress_percentage"] == 6.0
        assert mine["heavy-hitter"]["unlocked_at"] is None

    def test_every_collection_word_can_be_cast(self) -> None:
        from collections import Counter

        from backend.game.achievements import ANIMALS, ELEMENTS, PLANTS
        from backend.game.setup import LETTERS

        deck = {letter: spec[-1] for letter, spec in LETTERS.items()}  # copies
        for word in ANIMALS | PLANTS | ELEMENTS:
            assert word in match_ws.WORDS, word
            assert all(deck.get(c, 0) >= n for c, n in Counter(word).items()), word

    async def test_a_collection_counts_different_words_across_matches(
        self, session_maker, redis, alice, bob
    ) -> None:
        def game_casting(*casts):  # type: ignore[no-untyped-def]
            game = finished_game()
            for turn, (seat, word) in enumerate(casts, start=1):
                game.casts.append(
                    Cast(turn, seat, word, [Glyph(c, 1) for c in word], len(word))
                )
            return game

        first = await active_match(session_maker, alice, bob)
        await records.save_result(
            fake_app(redis),
            first,
            game_casting((0, "WOLF"), (1, "DOG"), (0, "CAT"), (0, "CAT"), (0, "ROSE")),
        )
        assert (await self.progress(session_maker, alice))["wild-wolf"] == (2, False)
        assert (await self.progress(session_maker, bob))["wild-wolf"] == (1, False)

        second = await active_match(session_maker, alice, bob, stats=False)
        await records.save_result(
            fake_app(redis),
            second,
            game_casting((0, "BEAR"), (0, "LION"), (0, "WOLF"), (0, "OWL")),
        )

        assert (await self.progress(session_maker, alice))["wild-wolf"] == (5, True)
        assert (await self.progress(session_maker, alice))["green-thumb"] == (1, False)
        # two matches' XP, First Steps and First Win, then the collection
        assert await self.xp(session_maker, alice) == 2 * 50 + 50 + 100 + 150

    async def test_the_sync_keeps_icons(self, session_maker) -> None:
        async with session_maker() as db:
            row = await db.get(Achievement, "first-win")
            row.icon_url, row.name = "/icons/first-win.png", "Renamed by hand"
            await db.commit()

        await records.sync_achievements()

        async with session_maker() as db:
            row = await db.get(Achievement, "first-win")
        assert (row.icon_url, row.name) == ("/icons/first-win.png", "First Win")


class TestAchievementRewards:
    @pytest.fixture
    async def perk(self, session_maker):  # type: ignore[no-untyped-def]
        from backend.models.perk import ModificationType, Perk, Rarity, TargetGlyphType

        async with session_maker() as db:
            db.add(
                Perk(
                    id="first_blood",
                    name="First Blood",
                    description="An achievement perk.",
                    rarity=Rarity.RARE,
                    target_glyph_type=TargetGlyphType.ANY,
                    modification_type=ModificationType.POWER_VALUE,
                    effect_payload={},
                )
            )
            await db.commit()

    def reward(self, monkeypatch, perk_id):  # type: ignore[no-untyped-def]
        """First Win gives this perk."""
        from dataclasses import replace

        rewarded = [
            replace(a, reward_perk_id=perk_id) if a.id == "first-win" else a
            for a in records.ACHIEVEMENTS
        ]
        monkeypatch.setattr(records, "ACHIEVEMENTS", rewarded)

    async def test_completing_it_unlocks_the_perk(
        self, session_maker, redis, alice, bob, alice_client, perk, monkeypatch
    ) -> None:
        self.reward(monkeypatch, "first_blood")
        await records.sync_achievements()
        match_id = await active_match(session_maker, alice, bob)

        await records.save_result(fake_app(redis), match_id, finished_game())

        loadout = (await alice_client.get("/users/me/loadout")).json()
        assert [p["id"] for p in loadout["unlocked_perks"]] == ["first_blood"]
        listed = (await alice_client.get("/achievements?size=100")).json()["items"]
        first_win = next(a for a in listed if a["id"] == "first-win")
        assert first_win["reward_perk"]["name"] == "First Blood"

    async def test_the_loser_does_not_get_it(
        self, session_maker, redis, alice, bob, bob_client, perk, monkeypatch
    ) -> None:
        self.reward(monkeypatch, "first_blood")
        await records.sync_achievements()
        match_id = await active_match(session_maker, alice, bob)

        await records.save_result(fake_app(redis), match_id, finished_game())

        loadout = (await bob_client.get("/users/me/loadout")).json()
        assert loadout["unlocked_perks"] == []

    async def test_an_unknown_reward_perk_stops_the_sync(self, monkeypatch) -> None:
        self.reward(monkeypatch, "no_such_perk")

        with pytest.raises(ValueError, match="no_such_perk"):
            await records.sync_achievements()


class DeadSocket:
    async def send_json(self, message: dict) -> None:
        raise WebSocketDisconnect(code=1006)


class LiveSocket:
    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.closed = False

    async def send_json(self, message: dict) -> None:
        self.messages.append(message)

    async def close(self) -> None:
        self.closed = True


class TestSending:
    async def test_a_dead_socket_does_not_stop_the_broadcast(self) -> None:
        match_ws.matches["m"] = new_match(seed=1)
        live = LiveSocket()
        match_ws.sockets["m"] = {0: DeadSocket(), 1: live}

        await match_ws.broadcast("m")

        assert live.messages[0]["type"] == "STATE"

    async def test_a_dead_socket_does_not_stop_send_to_others(self) -> None:
        live = LiveSocket()
        match_ws.sockets["m"] = {0: LiveSocket(), 1: DeadSocket(), 2: live}

        await match_ws.send_to_others("m", 0, {"type": "PING"})

        assert live.messages == [{"type": "PING"}]


@pytest.fixture
def client(monkeypatch):  # type: ignore[no-untyped-def]
    """Players are named by an x-user header: "a" sits in seat 0, "b" in seat 1."""

    async def user(ws):  # type: ignore[no-untyped-def]
        return ws.headers.get("x-user")

    async def seat(match_id, user_id):  # type: ignore[no-untyped-def]
        return {"a": 0, "b": 1}.get(user_id)

    ended: list[tuple[str, int, str]] = []

    async def end(app, match_id, game):  # type: ignore[no-untyped-def]
        ended.append((match_id, game.winner, game.end_reason))
        match_ws.matches.pop(match_id, None)

    monkeypatch.setattr(match_ws, "user_id_from_cookie", user)
    monkeypatch.setattr(match_ws, "seat_in_match", seat)

    async def setup(match_id):  # type: ignore[no-untyped-def]
        return 300, ("a", "b")  # five minutes each, and the names in the log

    monkeypatch.setattr(match_ws, "match_setup", setup)
    monkeypatch.setattr(match_ws, "end_match", end)
    monkeypatch.setattr(match_ws.settings, "CORS_ORIGINS", [ORIGIN])
    test_client = TestClient(app)
    test_client.ended = ended  # type: ignore[attr-defined]
    return test_client


def connect(client, match_id: str, player: str):  # type: ignore[no-untyped-def]
    return client.websocket_connect(
        f"/ws/matches/{match_id}", headers={"origin": ORIGIN, "x-user": player}
    )


def wait_for(condition, seconds: float = 2.0) -> None:  # type: ignore[no-untyped-def]
    deadline = time.monotonic() + seconds
    while not condition():
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.01)


class TestSocket:
    def test_bad_messages_are_rejected_and_the_socket_stays_open(self, client) -> None:  # type: ignore[no-untyped-def]
        match_id = str(uuid.uuid4())
        with connect(client, match_id, "a") as a, connect(client, match_id, "b") as b:
            a.receive_json()  # waiting state
            assert a.receive_json()["turn"] == 1
            b.receive_json()
            active = a if match_ws.matches[match_id].active_player_index == 0 else b

            for bad in (
                {"type": "CAST_WORD", "positions": ["x"]},
                {"type": "CAST_WORD", "positions": [True, False]},
                [1, 2],
                "hello",
                {"type": "DANCE"},
            ):
                active.send_json(bad)
                assert active.receive_json()["type"] == "ACTION_REJECTED"

            active.send_json({"type": "PASS_TURN"})
            passed = active.receive_json()
            assert passed["log"][-1] in ("a passed", "b passed")  # the players' names

    def test_match_ids_are_normalized(self, client) -> None:  # type: ignore[no-untyped-def]
        match_id = str(uuid.uuid4())
        with (
            connect(client, match_id.upper(), "a") as a,
            connect(client, match_id, "b") as b,
        ):
            a.receive_json()
            assert a.receive_json()["turn"] == 1  # both seats found the same match
            b.receive_json()

        assert list(match_ws.matches) == [match_id]

    def test_invalid_match_id_is_refused(self, client) -> None:  # type: ignore[no-untyped-def]
        with (
            pytest.raises(WebSocketDisconnect),
            connect(client, "not-a-uuid", "a") as a,
        ):
            a.receive_json()

    def test_a_player_who_never_arrives_aborts_the_match(
        self, client, monkeypatch
    ) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(match_ws, "GRACE_SECONDS", 0.05)
        aborted: list[str] = []

        async def abandon(app, match_id):  # type: ignore[no-untyped-def]
            aborted.append(match_id)

        monkeypatch.setattr(match_ws, "abandon", abandon)
        match_id = str(uuid.uuid4())

        with connect(client, match_id, "a") as a:
            a.receive_json()  # waiting for the opponent
            wait_for(lambda: aborted)  # fails, not hangs, if no timer fires
            assert a.receive_json() == {"type": "MATCH_ABORTED"}
            with pytest.raises(WebSocketDisconnect):
                a.receive_json()  # the server closed the socket

        assert aborted == [match_id]
        assert client.ended == []  # no winner: no rating or XP change

    def test_arriving_in_time_cancels_the_timer(self, client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(match_ws, "GRACE_SECONDS", 0.3)
        match_id = str(uuid.uuid4())

        with connect(client, match_id, "a") as a, connect(client, match_id, "b") as b:
            a.receive_json()
            started = a.receive_json()
            b.receive_json()
            time.sleep(0.4)

        assert started["turn"] == 1
        assert started["winner"] is None
        assert client.ended == []

    def test_the_result_is_shown_after_the_end(self, client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        async def result(match_id, user_id):  # type: ignore[no-untyped-def]
            return {"type": "STATE", "you_won": True} if user_id == "c" else None

        monkeypatch.setattr(match_ws, "final_result", result)

        with connect(client, str(uuid.uuid4()), "c") as c:
            assert c.receive_json() == {"type": "STATE", "you_won": True}
            with pytest.raises(WebSocketDisconnect):
                c.receive_json()

    def test_a_move_after_the_time_ran_out_ends_the_match(
        self, client, monkeypatch
    ) -> None:  # type: ignore[no-untyped-def]
        async def tiny(match_id):  # type: ignore[no-untyped-def]
            return 0.2, ("a", "b")  # seconds on each clock

        monkeypatch.setattr(match_ws, "match_setup", tiny)
        # No clock task: only the late message can notice the time ran out.
        monkeypatch.setattr(match_ws, "restart_clock", lambda *args: None)
        match_id = str(uuid.uuid4())

        with connect(client, match_id, "a") as a, connect(client, match_id, "b") as b:
            a.receive_json()
            a.receive_json()
            b.receive_json()
            late = a if match_ws.matches[match_id].active_player_index == 0 else b
            other = b if late is a else a
            time.sleep(0.3)

            late.send_json({"type": "PASS_TURN"})

            assert late.receive_json()["end_reason"] == "TIMEOUT"
            assert other.receive_json()["you_won"] is True
            assert late.receive_json()["reason"] == "Match is already over."
        assert client.ended[0][2] == "TIMEOUT"
