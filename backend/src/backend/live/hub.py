"""Live matches: the game engine connected to players' sockets.

One MatchHub runs per backend process. For each match it keeps the engine
state (also saved in Redis after every change, so a restart can pick it up),
the players' open connections, the clock timer and disconnect timers.

    hub.connect(match_id, user_id, send) -> Connection   on socket open
    hub.receive(connection, message)                     each client message
    hub.disconnect(connection)                           on socket close
    hub.resign(match_id, user_id)                        REST abandon

Messages use the API spec's envelope { type, data, seq }. After every move each
connected player also gets a fresh MATCH_STATE, so the client can simply
render the latest snapshot.

Limitation: matches live in one process's memory, so run one backend worker
(as `fastapi dev` does). Several workers would need routing by match id.
"""

import asyncio
import contextlib
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select

from backend.core.dictionary import load_word_list
from backend.core.identifiers import user_id_to_bytes, user_id_to_string
from backend.core.matchmaking_store import MatchmakingQueueStore
from backend.game.clock import deadline_ms
from backend.game.piles import new_match
from backend.game.state import EndReason, MatchState, Phase
from backend.game.turns import (
    Event,
    EventType,
    MatchRules,
    apply,
    check_timeout,
    forfeit,
    match_state,
    parse_action,
)
from backend.live.results import SessionFactory, save_cast, save_result
from backend.models.achievement_words import AchievementWord
from backend.models.match import Match, MatchStatus

Send = Callable[[dict[str, Any]], Awaitable[None]]

STATE_TTL_SECONDS = 24 * 60 * 60
ENDED_TTL_SECONDS = 60 * 60


def wall_clock_ms() -> int:
    return int(time.time() * 1000)


class MatchAccessError(Exception):
    """The user can't use this match; `status` is the matching HTTP code."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


@dataclass(eq=False)
class Connection:
    match_id: str
    player: int
    send: Send


@dataclass(eq=False)
class LiveMatch:
    state: MatchState
    rules: MatchRules
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    connections: list[Connection] = field(default_factory=list)
    seq: int = 0
    timer: asyncio.Task[None] | None = None
    absent: dict[int, asyncio.Task[None]] = field(default_factory=dict)

    def connected(self, player: int) -> bool:
        return any(c.player == player for c in self.connections)


class MatchHub:
    def __init__(
        self,
        redis: Redis,
        session_factory: SessionFactory,
        *,
        grace_seconds: float = 30,
        arrival_seconds: float = 60,
        clock: Callable[[], int] = wall_clock_ms,
        rules: MatchRules | None = None,
    ) -> None:
        self.redis = redis
        self.session_factory = session_factory
        self.grace_seconds = grace_seconds
        self.arrival_seconds = arrival_seconds
        self.clock = clock
        self._rules = rules
        self.matches: dict[str, LiveMatch] = {}
        self._loading = asyncio.Lock()

    # Loading ---------------------------------------------------------------

    @staticmethod
    def _key(match_id: str) -> str:
        return f"live:match:{match_id}"

    async def _rules_for_match(self) -> MatchRules:
        if self._rules is not None:
            return self._rules
        async with self.session_factory() as session:
            words = (await session.scalars(select(AchievementWord.word))).all()
        return MatchRules(load_word_list(), achievement_words=frozenset(words))

    async def _load(self, match_id: str) -> LiveMatch:
        async with self._loading:
            live = self.matches.get(match_id)
            if live is not None:
                return live
            saved = await self.redis.get(self._key(match_id))
            if saved is not None:
                state = MatchState.from_dict(json.loads(saved))
            else:
                async with self.session_factory() as session:
                    match = await session.get(Match, user_id_to_bytes(match_id))
                if match is None:
                    raise MatchAccessError("Match not found", 404)
                if match.status != MatchStatus.ACTIVE or match.player2_id is None:
                    raise MatchAccessError("This match is not being played", 400)
                state = new_match(
                    match_id,
                    (
                        user_id_to_string(match.player1_id),
                        user_id_to_string(match.player2_id),
                    ),
                    match.time_control_seconds,
                )
                await self._save(state)
            live = LiveMatch(state, await self._rules_for_match())
            self.matches[match_id] = live
            return live

    async def _save(self, state: MatchState) -> None:
        ttl = ENDED_TTL_SECONDS if state.phase == Phase.ENDED else STATE_TTL_SECONDS
        await self.redis.set(
            self._key(state.match_id), json.dumps(state.to_dict()), ex=ttl
        )

    # Sending ---------------------------------------------------------------

    async def _send(
        self, live: LiveMatch, players: tuple[int, ...], kind: str, data: dict[str, Any]
    ) -> None:
        live.seq += 1
        message = {"type": kind, "data": data, "seq": live.seq}
        for connection in list(live.connections):
            if connection.player in players:
                with contextlib.suppress(Exception):
                    await connection.send(message)

    async def _send_snapshots(self, live: LiveMatch) -> None:
        now = self.clock()
        for player in (0, 1):
            if live.connected(player):
                event = match_state(live.state, player, now)
                await self._send(live, (player,), event.type.value, event.data)

    # Changing the state ----------------------------------------------------

    async def _commit(
        self, live: LiveMatch, state: MatchState, events: list[Event]
    ) -> None:
        """Store a new state, record it in MySQL, and tell the players. Call
        with live.lock held."""
        changed = state is not live.state
        live.state = state
        if changed:
            await self._save(state)
        for event in events:
            if event.type == EventType.WORD_RESOLVED:
                await save_cast(self.session_factory, state, event.data)
            if event.type == EventType.MATCH_ENDED:
                event.data["elo_delta"] = await save_result(self.session_factory, state)
                await self._after_end(live)
        for event in events:
            await self._send(live, event.to, event.type.value, event.data)
        if changed:
            await self._send_snapshots(live)
            self._schedule_timer(live)

    async def _after_end(self, live: LiveMatch) -> None:
        current = asyncio.current_task()
        for task in (live.timer, *live.absent.values()):
            if task is not None and task is not current:
                task.cancel()
        live.absent.clear()
        live.timer = None
        # Free both players to queue or host again.
        queue = MatchmakingQueueStore(self.redis)
        for player in live.state.players:
            await queue.clear_matched_ticket(player.user_id)

    def _schedule_timer(self, live: LiveMatch) -> None:
        if live.timer is not None and live.timer is not asyncio.current_task():
            live.timer.cancel()
        live.timer = None
        deadline = deadline_ms(live.state)
        if deadline is not None:
            live.timer = asyncio.create_task(self._timeout_at(live, deadline))

    async def _timeout_at(self, live: LiveMatch, deadline: int) -> None:
        await asyncio.sleep(max(0.0, (deadline - self.clock()) / 1000))
        async with live.lock:
            state, events = check_timeout(live.state, max(self.clock(), deadline))
            if events:
                await self._commit(live, state, events)

    async def _end_by_absence(
        self, live: LiveMatch, player: int, seconds: float
    ) -> None:
        await asyncio.sleep(seconds)
        async with live.lock:
            live.absent.pop(player, None)
            if live.connected(player) or live.state.phase == Phase.ENDED:
                return
            state, events = forfeit(
                live.state, player, EndReason.DISCONNECT, self.clock()
            )
            await self._commit(live, state, events)

    # Public API ------------------------------------------------------------

    async def connect(self, match_id: str, user_id: str, send: Send) -> Connection:
        live = await self._load(match_id)
        async with live.lock:
            ids = [p.user_id for p in live.state.players]
            if user_id not in ids:
                raise MatchAccessError("You are not a player in this match", 403)
            player = ids.index(user_id)
            returning = player in live.absent
            if returning:
                live.absent.pop(player).cancel()
            connection = Connection(match_id, player, send)
            live.connections.append(connection)
            if live.state.phase != Phase.ENDED:
                if returning:
                    await self._send(live, (1 - player,), "OPPONENT_RECONNECTED", {})
                other = 1 - player
                if not live.connected(other) and other not in live.absent:
                    # The opponent hasn't arrived yet: give them a while.
                    live.absent[other] = asyncio.create_task(
                        self._end_by_absence(live, other, self.arrival_seconds)
                    )
            event = match_state(live.state, player, self.clock())
            await self._send(live, (player,), event.type.value, event.data)
            return connection

    async def disconnect(self, connection: Connection) -> None:
        live = self.matches.get(connection.match_id)
        if live is None:
            return
        async with live.lock:
            if connection in live.connections:
                live.connections.remove(connection)
            player = connection.player
            if live.state.phase == Phase.ENDED or live.connected(player):
                return
            await self._send(
                live,
                (1 - player,),
                "OPPONENT_DISCONNECTED",
                {"grace_seconds": self.grace_seconds},
            )
            if player not in live.absent:
                live.absent[player] = asyncio.create_task(
                    self._end_by_absence(live, player, self.grace_seconds)
                )

    async def receive(self, connection: Connection, message: Any) -> None:
        live = self.matches[connection.match_id]
        player = connection.player
        kind = message.get("type") if isinstance(message, dict) else None
        async with live.lock:
            if kind == "PING":
                data = (
                    message.get("data") if isinstance(message.get("data"), dict) else {}
                )
                await self._send(live, (player,), "PONG", {"ts": data.get("ts")})
                return
            if kind == "SURRENDER":
                state, events = forfeit(
                    live.state, player, EndReason.RESIGNATION, self.clock()
                )
                await self._commit(live, state, events)
                return
            action = (
                parse_action(player, message) if isinstance(message, dict) else None
            )
            if action is None:
                await self._send(
                    live,
                    (player,),
                    "ERROR",
                    {
                        "code": "UNKNOWN_MESSAGE",
                        "detail": f"Unknown message type {kind!r}.",
                    },
                )
                return
            state, events = apply(live.state, action, self.clock(), live.rules)
            await self._commit(live, state, events)

    async def resign(self, match_id: str, user_id: str) -> None:
        """End the match as a resignation by `user_id` (REST abandon)."""
        live = await self._load(match_id)
        async with live.lock:
            ids = [p.user_id for p in live.state.players]
            if user_id not in ids:
                raise MatchAccessError("You are not a player in this match", 403)
            state, events = forfeit(
                live.state, ids.index(user_id), EndReason.RESIGNATION, self.clock()
            )
            await self._commit(live, state, events)

    async def close(self) -> None:
        for live in self.matches.values():
            for task in (live.timer, *live.absent.values()):
                if task is not None:
                    task.cancel()
