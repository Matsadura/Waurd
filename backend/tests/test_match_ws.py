"""The match WebSocket: saving results, sending, bad messages, arrival, ids."""

import json
import time
import uuid
from types import SimpleNamespace

import pytest

match_ws = pytest.importorskip(
    "backend.ws.match_ws", reason="The match socket is not merged yet"
)

from backend.game.rules import resign
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
    monkeypatch.setattr(match_ws, "async_session_maker", session_maker)
    yield
    for task in match_ws.timers.values():
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

        await match_ws.save_result(fake_app(redis), match_id, finished_game())

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

        async def broken(db, record):  # type: ignore[no-untyped-def]
            raise RuntimeError("stats exploded")

        monkeypatch.setattr(match_ws, "update_stats", broken)
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


class DeadSocket:
    async def send_json(self, message: dict) -> None:
        raise WebSocketDisconnect(code=1006)


class LiveSocket:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def send_json(self, message: dict) -> None:
        self.messages.append(message)


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

    def test_a_player_who_never_arrives_loses(self, client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(match_ws, "GRACE_SECONDS", 0.05)
        match_id = str(uuid.uuid4())

        with connect(client, match_id, "a") as a:
            a.receive_json()  # waiting for the opponent
            wait_for(lambda: client.ended)  # fails, not hangs, if no timer fires
            assert a.receive_json()["winner"] == 0

        assert client.ended == [(match_id, 0, "DISCONNECT")]

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
