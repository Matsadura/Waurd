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

from backend.game.rules import cast_word, resign, start_turn, use_time
from backend.game.models import Glyph
from backend.game.setup import new_match
from fastapi import WebSocketDisconnect
from starlette.testclient import TestClient

from backend.main import app
from backend.models import Match, MatchStatus, UserStats

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


async def active_match(session_maker, alice, bob) -> str:  # type: ignore[no-untyped-def]
    match_id = uuid.uuid4()
    async with session_maker() as db:
        # Registration gives every user a stats row.
        for user in (alice, bob):
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

    def test_each_player_gets_half_the_time_control(self) -> None:
        game = new_match(seed=1, time_control_seconds=300)

        assert [player.time_left for player in game.players] == [150, 150]

    def test_only_the_active_players_clock_runs(self) -> None:
        game = self.started()
        first = game.active_player_index

        use_time(game, 20.0)

        assert game.players[first].time_left == 130
        assert game.players[1 - first].time_left == 150

    def test_a_long_turn_does_not_pass_on_its_own(self) -> None:
        game = self.started()

        use_time(game, 100.0)

        assert (game.turn, game.winner) == (1, None)

    def test_running_out_of_time_loses(self) -> None:
        game = self.started(seconds=10)  # 5 seconds each
        first = game.active_player_index

        use_time(game, 5.0)

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
        game.players[0].time_left, game.players[1].time_left = 60, 80  # of 90 each

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
            "glyphs": [{"letter": "A", "damage": 6}, {"letter": "T", "damage": 8}]
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

    async def five_minutes(match_id):  # type: ignore[no-untyped-def]
        return 300

    monkeypatch.setattr(match_ws, "time_control", five_minutes)
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
            assert active.receive_json()["type"] == "STATE"

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
            return 0.4  # 0.2 seconds each

        monkeypatch.setattr(match_ws, "time_control", tiny)
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
