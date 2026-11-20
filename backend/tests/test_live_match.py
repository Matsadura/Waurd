"""Live matches: the MatchHub that runs the engine for connected players."""

import asyncio
import json
import uuid
from dataclasses import replace

import pytest

pytest.importorskip("backend.live.hub", reason="Live matches are not merged yet")

from backend.live.hub import MatchAccessError, MatchHub
from backend.live.results import elo_after
from sqlalchemy import select

from backend.core.matchmaking_store import MatchmakingQueueStore
from backend.game.perks import load_catalog
from backend.game.state import Glyph
from backend.game.turns import MatchRules
from backend.models import Match, MatchCast, MatchStatus, UserStats
from backend.models.match import MatchEndReason

WORDS = frozenset({"CAB", "AT", "TA", "BAT"})
NO_PERKS = {pid: replace(spec, ready=False) for pid, spec in load_catalog().items()}
RULES = MatchRules(WORDS, catalog=NO_PERKS)


def uid(user) -> str:  # type: ignore[no-untyped-def]
    return str(uuid.UUID(bytes=user.id))


class Clock:
    def __init__(self) -> None:
        self.ms = 1_000_000

    def __call__(self) -> int:
        return self.ms


class Player:
    """A fake socket: collects what the hub sends."""

    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def send(self, message: dict) -> None:
        self.messages.append(message)

    def types(self) -> list[str]:
        return [m["type"] for m in self.messages]

    def last(self, kind: str) -> dict:
        return next(m["data"] for m in reversed(self.messages) if m["type"] == kind)


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def hub(redis, session_maker, clock) -> MatchHub:  # type: ignore[no-untyped-def]
    return MatchHub(
        redis,
        session_maker,
        grace_seconds=0.05,
        arrival_seconds=0.1,
        clock=clock,
        rules=RULES,
    )


@pytest.fixture
async def match_id(session_maker, alice, bob) -> str:  # type: ignore[no-untyped-def]
    match_id = uuid.uuid4()
    async with session_maker() as session:
        session.add(
            Match(
                id=match_id.bytes,
                player1_id=alice.id,
                player2_id=bob.id,
                time_control_seconds=180,
                status=MatchStatus.ACTIVE,
            )
        )
        await session.commit()
    return str(match_id)


async def start(hub: MatchHub, match_id: str, alice, bob):  # type: ignore[no-untyped-def]
    a, b = Player(), Player()
    ca = await hub.connect(match_id, uid(alice), a.send)
    cb = await hub.connect(match_id, uid(bob), b.send)
    await hub.receive(ca, {"type": "PLAYER_READY", "data": {}})
    await hub.receive(cb, {"type": "PLAYER_READY", "data": {}})
    return a, b, ca, cb


def active(hub: MatchHub, match_id: str, ca, cb):  # type: ignore[no-untyped-def]
    state = hub.matches[match_id].state
    return (ca, cb) if state.active_player == ca.player else (cb, ca)


def give_hand(
    hub: MatchHub, match_id: str, player: int, *letters: str, value: int = 30
) -> None:
    from backend.game.config import Effect, GlyphType

    side = hub.matches[match_id].state.players[player]
    side.hand = [
        Glyph(f"x-{i}", letter, GlyphType.POWER, Effect.DAMAGE, value)
        for i, letter in enumerate(letters)
    ]


class TestJoining:
    async def test_connect_sends_a_snapshot(self, hub, match_id, alice) -> None:
        player = Player()

        connection = await hub.connect(match_id, uid(alice), player.send)

        assert connection.player == 0
        [message] = player.messages
        assert message["type"] == "MATCH_STATE"
        assert message["seq"] == 1
        assert message["data"]["phase"] == "WAITING"
        assert message["data"]["max_hp"] == 130

    async def test_strangers_cannot_join(self, hub, match_id, carol) -> None:
        with pytest.raises(MatchAccessError) as caught:
            await hub.connect(match_id, uid(carol), Player().send)
        assert caught.value.status == 403

    async def test_unknown_match(self, hub, alice) -> None:
        with pytest.raises(MatchAccessError) as caught:
            await hub.connect(str(uuid.uuid4()), uid(alice), Player().send)
        assert caught.value.status == 404

    async def test_waiting_lobby_is_not_playable(
        self, hub, session_maker, alice
    ) -> None:
        lobby = uuid.uuid4()
        async with session_maker() as session:
            session.add(
                Match(
                    id=lobby.bytes,
                    player1_id=alice.id,
                    time_control_seconds=180,
                    status=MatchStatus.WAITING,
                )
            )
            await session.commit()

        with pytest.raises(MatchAccessError) as caught:
            await hub.connect(str(lobby), uid(alice), Player().send)
        assert caught.value.status == 400

    async def test_both_ready_starts_the_match(self, hub, match_id, alice, bob) -> None:
        a, b, _ca, _cb = await start(hub, match_id, alice, bob)

        assert "MATCH_START" in a.types() and "MATCH_START" in b.types()
        first = hub.matches[match_id].state.active_player
        starter = a if first == 0 else b
        waiter = b if first == 0 else a
        assert "TURN_START" in starter.types() and "TURN_START" not in waiter.types()
        assert "OPPONENT_TURN_START" in waiter.types()
        assert len(starter.last("MATCH_STATE")["hand"]) == 7
        assert waiter.last("MATCH_STATE")["hand"] is None

    async def test_seq_only_grows(self, hub, match_id, alice, bob) -> None:
        a, _, _, _ = await start(hub, match_id, alice, bob)
        seqs = [m["seq"] for m in a.messages]
        assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)


class TestPlaying:
    async def test_cast_reaches_both_and_is_recorded(
        self, hub, match_id, alice, bob, session_maker
    ) -> None:
        a, b, ca, cb = await start(hub, match_id, alice, bob)
        me, _ = active(hub, match_id, ca, cb)
        give_hand(hub, match_id, me.player, "C", "A", "B", value=5)

        await hub.receive(
            me, {"type": "CAST_WORD", "data": {"turn": 1, "glyph_sequence": [0, 1, 2]}}
        )

        assert (
            a.last("WORD_RESOLVED")["word"] == "CAB" == b.last("WORD_RESOLVED")["word"]
        )
        async with session_maker() as session:
            [cast] = (await session.scalars(select(MatchCast))).all()
        assert (cast.turn_number, cast.word_played, cast.damage_dealt) == (1, "CAB", 15)
        assert cast.glyphs_payload["steps"][0]["letters"] == "C"
        assert hub.matches[match_id].state.turn == 2

    async def test_rejected_move_goes_to_the_sender_only(
        self, hub, match_id, alice, bob
    ) -> None:
        a, b, ca, cb = await start(hub, match_id, alice, bob)
        me, _other = active(hub, match_id, ca, cb)
        mine, theirs = (a, b) if me is ca else (b, a)
        before = len(theirs.messages)

        await hub.receive(
            me, {"type": "CAST_WORD", "data": {"turn": 9, "glyph_sequence": [0]}}
        )

        assert mine.last("ACTION_REJECTED")["code"] == "WRONG_TURN"
        assert len(theirs.messages) == before

    async def test_ping_and_unknown_messages(self, hub, match_id, alice, bob) -> None:
        a, _, ca, _ = await start(hub, match_id, alice, bob)

        await hub.receive(ca, {"type": "PING", "data": {"ts": 42}})
        await hub.receive(ca, {"type": "DANCE", "data": {}})
        await hub.receive(ca, "not even a dict")

        assert a.last("PONG") == {"ts": 42}
        assert a.types()[-2:] == ["ERROR", "ERROR"]

    async def test_state_survives_a_restart(
        self, hub, match_id, alice, bob, redis, session_maker, clock
    ) -> None:
        await start(hub, match_id, alice, bob)
        turn = hub.matches[match_id].state.turn
        await hub.close()

        restarted = MatchHub(redis, session_maker, clock=clock, rules=RULES)
        player = Player()
        await restarted.connect(match_id, uid(alice), player.send)

        assert player.last("MATCH_STATE")["turn"] == turn
        assert json.loads(await redis.get(f"live:match:{match_id}"))["turn"] == turn


class TestEnding:
    async def test_surrender_saves_the_result_and_elo(
        self, hub, match_id, alice, bob, session_maker, redis
    ) -> None:
        _a, b, ca, _cb = await start(hub, match_id, alice, bob)
        queue = MatchmakingQueueStore(redis)
        for user in (alice, bob):
            await redis.set(
                f"matchmaking:user:{uid(user)}",
                json.dumps({"status": "MATCHED", "matched_match_id": match_id}),
            )

        await hub.receive(ca, {"type": "SURRENDER", "data": {}})

        ended = b.last("MATCH_ENDED")
        assert ended["winner_id"] == uid(bob)
        assert ended["end_reason"] == "RESIGNATION"
        assert ended["elo_delta"] == {uid(alice): -16, uid(bob): 16}
        async with session_maker() as session:
            match = await session.get(Match, uuid.UUID(match_id).bytes)
            stats = {
                s.user_id: s for s in (await session.scalars(select(UserStats))).all()
            }
        assert match.status == MatchStatus.FINISHED
        assert match.end_reason == MatchEndReason.RESIGNATION
        assert match.winner_id == bob.id
        assert (match.player1_elo_before, match.player1_elo_after) == (1200, 1184)
        assert (match.player2_elo_before, match.player2_elo_after) == (1200, 1216)
        assert (stats[alice.id].losses, stats[bob.id].wins) == (1, 1)
        assert stats[bob.id].rating_elo == 1216
        assert await queue.get_user_ticket(uid(alice)) is None

    async def test_knockout_records_stats(
        self, hub, match_id, alice, bob, session_maker
    ) -> None:
        a, _b, ca, cb = await start(hub, match_id, alice, bob)
        me, other = active(hub, match_id, ca, cb)
        hub.matches[match_id].state.players[other.player].hp = 10
        hub.matches[match_id].state.players[other.player].defense = 0
        give_hand(hub, match_id, me.player, "B", "A", "T", value=30)

        await hub.receive(
            me, {"type": "CAST_WORD", "data": {"turn": 1, "glyph_sequence": [0, 1, 2]}}
        )

        assert a.last("MATCH_ENDED")["end_reason"] == "HEALTH_DEPLETED"
        winner = alice if me is ca else bob
        async with session_maker() as session:
            match = await session.get(Match, uuid.UUID(match_id).bytes)
            stats = await session.get(UserStats, winner.id)
        assert match.winner_id == winner.id
        assert match.total_turns == 1
        assert (
            stats.highest_scoring_word,
            stats.highest_word_score,
            stats.total_damage_dealt,
        ) == ("BAT", 90, 90)

    async def test_saving_twice_changes_nothing(
        self, hub, match_id, alice, bob, session_maker
    ) -> None:
        _, _, ca, _ = await start(hub, match_id, alice, bob)
        await hub.receive(ca, {"type": "SURRENDER", "data": {}})
        await hub.resign(match_id, uid(alice))  # already over

        async with session_maker() as session:
            stats = await session.get(UserStats, bob.id)
        assert stats.matches_played == 1

    async def test_clock_timer_ends_the_match(
        self, hub, match_id, alice, bob, clock
    ) -> None:
        a, _, _ca, _cb = await start(hub, match_id, alice, bob)
        live = hub.matches[match_id]
        late = live.state.players[live.state.active_player].user_id

        clock.ms += 180_001
        hub._schedule_timer(live)  # the real timer would wake at the deadline
        await asyncio.sleep(0.05)

        ended = a.last("MATCH_ENDED")
        assert ended["end_reason"] == "TIMEOUT"
        assert ended["winner_id"] != late

    async def test_disconnect_then_grace_runs_out(
        self, hub, match_id, alice, bob
    ) -> None:
        a, _b, _ca, cb = await start(hub, match_id, alice, bob)

        await hub.disconnect(cb)
        assert a.last("OPPONENT_DISCONNECTED") == {"grace_seconds": 0.05}
        await asyncio.sleep(0.12)

        ended = a.last("MATCH_ENDED")
        assert (ended["end_reason"], ended["winner_id"]) == ("DISCONNECT", uid(alice))

    async def test_coming_back_in_time_continues(
        self, hub, match_id, alice, bob
    ) -> None:
        a, _, _ca, cb = await start(hub, match_id, alice, bob)

        await hub.disconnect(cb)
        b2 = Player()
        await hub.connect(match_id, uid(bob), b2.send)
        await asyncio.sleep(0.12)

        assert "OPPONENT_RECONNECTED" in a.types()
        assert "MATCH_ENDED" not in a.types()
        assert b2.messages[-1]["type"] == "MATCH_STATE"

    async def test_a_player_who_never_arrives_loses(self, hub, match_id, alice) -> None:
        a = Player()
        await hub.connect(match_id, uid(alice), a.send)

        await asyncio.sleep(0.2)

        assert a.last("MATCH_ENDED")["winner_id"] == uid(alice)

    async def test_resign_checks_the_player(self, hub, match_id, carol) -> None:
        with pytest.raises(MatchAccessError) as caught:
            await hub.resign(match_id, uid(carol))
        assert caught.value.status == 403


def test_elo() -> None:
    assert elo_after(1200, 1200, 1.0) == 1216
    assert elo_after(1200, 1200, 0.0) == 1184
    # Beating a much stronger player is worth more than beating a weaker one.
    assert elo_after(1200, 1600, 1.0) - 1200 > elo_after(1600, 1200, 1.0) - 1600
