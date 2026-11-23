"""Live games over the WebSocket: the games in memory, sockets and timers."""

import asyncio
import logging
import uuid
from pathlib import Path

from backend.core.config import settings
from backend.core.session_store import RedisSessionStore
from backend.game.models import Match
from backend.game.rules import (
    cast_word,
    lose_by_disconnect,
    pass_turn,
    resign,
    start_turn,
)
from backend.game.setup import load_words, new_match
from backend.ws.records import abandon, final_result, save_result, seat_in_match
from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect

logger = logging.getLogger("uvicorn.error")

router = APIRouter()
DATA_DIR = Path(__file__).parent.parent / "data"
WORDS = load_words(DATA_DIR / "enable1.txt")
matches: dict[str, Match] = {}
sockets: dict[str, dict[int, WebSocket]] = {}

GRACE_SECONDS = 30
timers: dict[tuple[str, int], asyncio.Task] = {}


async def user_id_from_cookie(ws: WebSocket) -> str | None:
    """The logged-in user's id, read the same way get_current_user does."""
    session_id = ws.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_id:
        return None
    store = RedisSessionStore(
        ws.app.state.redis, ttl_seconds=settings.SESSION_TTL_SECONDS
    )
    session = await store.get_session(session_id)
    return session["user_id"] if session else None


async def end_match(app: FastAPI, match_id: str, match: Match) -> None:
    if matches.pop(match_id, None) is None:
        return  # already ended
    try:
        await save_result(app, match_id, match)
    except Exception:
        logger.exception("Could not save result of match %s", match_id)
    matches.pop(match_id, None)


async def resign_live(app: FastAPI, match_id: str, user_id: str) -> bool:
    """Resign a game being played over the socket. False if there is none."""
    match = matches.get(match_id)
    if match is None or match.winner is not None:
        return False
    me = await seat_in_match(match_id, user_id)
    if me is None:
        return False
    resign(match, me)
    await broadcast(match_id)
    await end_match(app, match_id, match)
    return True


async def end_if_still_gone(app: FastAPI, match_id: str, me: int) -> None:
    """After the grace period, a player who left or never arrived loses."""
    await asyncio.sleep(GRACE_SECONDS)
    timers.pop((match_id, me), None)
    match = matches.get(match_id)
    if match is None or match.winner is not None:
        return
    if match.turn == 0 and not sockets.get(match_id):
        await abandon(app, match_id)  # neither player is here: no winner
        matches.pop(match_id, None)
        return
    lose_by_disconnect(match, me)
    await broadcast(match_id)
    await end_match(app, match_id, match)


async def left(ws: WebSocket, match_id: str, me: int) -> None:
    """A socket closed: forget it, and start the forfeit timer if the game is live."""
    seats = sockets.get(match_id, {})
    if seats.get(me) is not ws:
        return  # this seat already has a newer connection, so the player isn't gone
    del seats[me]
    if not seats:
        del sockets[match_id]

    match = matches.get(match_id)
    if match is None or match.winner is not None:
        return
    if match.turn > 0:
        await send_to_others(
            match_id,
            me,
            {"type": "OPPONENT_DISCONNECTED", "grace_seconds": GRACE_SECONDS},
        )
    timers[(match_id, me)] = asyncio.create_task(
        end_if_still_gone(ws.app, match_id, me)
    )


def view(match: Match, me: int) -> dict:
    """What one player is allowed to see: their own hand, never the opponent's."""
    player = match.players[me]
    opponent = match.players[1 - me]
    return {
        "type": "STATE",
        "turn": match.turn,
        "your_turn": match.active_player_index == me,
        "winner": match.winner,
        "you_won": None if match.winner is None else match.winner == me,
        "end_reason": match.end_reason,
        "you": {
            "hp": player.hp,
            "hand": [
                {"position": i, "letter": glyph.letter, "damage": glyph.damage}
                for i, glyph in enumerate(player.hand)
            ],
        },
        "opponent": {"hp": opponent.hp, "hand_size": len(opponent.hand)},
    }


async def broadcast(match_id: str) -> None:
    match = matches[match_id]
    for me, socket in list(sockets.get(match_id, {}).items()):
        try:
            await socket.send_json(view(match, me))
        except (WebSocketDisconnect, RuntimeError):
            pass  # that player's own loop notices the drop and cleans up


async def send_to_others(match_id: str, me: int, message: dict) -> None:
    for seat, socket in list(sockets.get(match_id, {}).items()):
        if seat == me:
            continue
        try:
            await socket.send_json(message)
        except (WebSocketDisconnect, RuntimeError):
            pass  # that player's own loop notices the drop and cleans up


@router.websocket("/matches/{match_id}")
async def play(ws: WebSocket, match_id: str) -> None:
    try:
        match_id = str(uuid.UUID(match_id))  # one spelling per match
    except ValueError:
        await ws.close()
        return

    origin = ws.headers.get("origin")
    if origin not in settings.CORS_ORIGINS:
        logger.info("WS rejected: origin %r is not allowed", origin)
        await ws.close()
        return

    user_id = await user_id_from_cookie(ws)
    if user_id is None:
        logger.info("WS rejected: no valid session cookie")
        await ws.close()
        return

    me = await seat_in_match(match_id, user_id)
    if me is None:
        result = await final_result(match_id, user_id)
        if result is None:
            logger.info(
                "WS rejected: user %s has no seat in match %s", user_id, match_id
            )
            await ws.close()
            return
        await ws.accept()  # the match is over: show its result and say goodbye
        await ws.send_json(result)
        await ws.close()
        return

    await ws.accept()
    if match_id not in matches:
        matches[match_id] = new_match(seed=None)
    sockets.setdefault(match_id, {})[me] = ws
    match = matches[match_id]

    timer = timers.pop((match_id, me), None)
    if timer is not None:
        timer.cancel()
        if match.turn > 0:
            await send_to_others(match_id, me, {"type": "OPPONENT_RECONNECTED"})

    other = 1 - me
    if (
        match.turn == 0
        and other not in sockets[match_id]
        and (match_id, other) not in timers
    ):
        # The opponent hasn't arrived yet: they lose if they don't within the grace period.
        timers[(match_id, other)] = asyncio.create_task(
            end_if_still_gone(ws.app, match_id, other)
        )

    if len(sockets[match_id]) == 2 and match.turn == 0:
        start_turn(match)
    await broadcast(match_id)

    try:
        while True:
            try:
                message = await ws.receive_json()
                if match.turn == 0:
                    raise ValueError("Waiting for the other player.")
                if message["type"] == "CAST_WORD":
                    cast_word(match, me, message["positions"], WORDS)
                elif message["type"] == "PASS_TURN":
                    pass_turn(match, me)
                elif message["type"] == "RESIGN":
                    resign(match, me)
                else:
                    raise ValueError("Unknown action.")
            except (ValueError, KeyError, TypeError) as error:
                await ws.send_json({"type": "ACTION_REJECTED", "reason": str(error)})
                continue
            await broadcast(match_id)
            if match.winner is not None:
                await end_match(ws.app, match_id, match)
    except WebSocketDisconnect:
        await left(ws, match_id, me)
