import uuid
from pathlib import Path

from backend.core.config import settings
from backend.core.identifiers import user_id_to_bytes, user_id_to_string
from backend.core.matchmaking_store import MatchmakingQueueStore
from backend.core.session_store import RedisSessionStore
from backend.db.session import async_session_maker
from backend.game.models import Match
from backend.game.rules import cast_word, pass_turn, start_turn
from backend.game.setup import load_words, new_match
from backend.models.match import MatchStatus
from backend.repositories.match import MatchRepository
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
DATA_DIR = Path(__file__).parent.parent / "data"
WORDS = load_words(DATA_DIR / "enable1.txt")
matches: dict[str, Match] = {}
sockets: dict[int, list[WebSocket]] = {}


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


async def seat_in_match(match_id: str, user_id: str) -> int | None:
    """0 if the user is player1 of this active match, 1 if player2, else None."""
    try:
        match_id_bytes = uuid.UUID(match_id).bytes
    except ValueError:
        return None
    async with async_session_maker() as db:
        record = await MatchRepository(db).get_match_by_id(match_id_bytes)
    if record is None or record.status != MatchStatus.ACTIVE:
        return None

    user_id_bytes = user_id_to_bytes(user_id)
    if record.player1_id == user_id_bytes:
        return 0
    if record.player2_id == user_id_bytes:
        return 1
    return None


async def save_result(ws: WebSocket, match_id: str, match: Match) -> None:
    """Write the result to MySQL, then let both players queue again."""
    async with async_session_maker() as db:
        record = await MatchRepository(db).finish_match(
            uuid.UUID(match_id).bytes,
            winner_seat=match.winner,
            player1_hp=match.players[0].hp,
            player2_hp=match.players[1].hp,
            total_turns=match.turn,
        )
        await db.commit()

    queue_store = MatchmakingQueueStore(ws.app.state.redis)
    for player_id in (record.player1_id, record.player2_id):
        await queue_store.clear_matched_ticket(user_id_to_string(player_id))


def view(match: Match, me: int) -> dict:
    """What one player is allowed to see: their own hand, never the opponent's."""
    player = match.players[me]
    opponent = match.players[1 - me]
    return {
        "type": "STATE",
        "turn": match.turn,
        "your_turn": match.active_player_index == me,
        "winner": match.winner,
        "you": {
            "hp": player.hp,
            # "hand": [[glyph.letter, glyph.damage] for glyph in player.hand],
            "hand": [
                {"position": i, "letter": glyph.letter, "damage": glyph.damage}
                for i, glyph in enumerate(player.hand)
            ],
        },
        "opponent": {"hp": opponent.hp, "hand_size": len(opponent.hand)},
    }


async def broadcast(match_id: str) -> None:
    """Send the current state to all players in a match."""
    match = matches[match_id]
    for me, socket in sockets[match_id].items():
        await socket.send_json(view(match, me))


@router.websocket("/matches/{match_id}")
async def play(ws: WebSocket, match_id: str) -> None:
    if ws.headers.get("origin") not in settings.CORS_ORIGINS:
        await ws.close()
        return
    user_id = await user_id_from_cookie(ws)
    me = await seat_in_match(match_id, user_id) if user_id else None
    if me is None:
        await ws.close()
        return
    await ws.accept()
    if match_id not in matches:
        matches[match_id] = new_match(seed=None)
        sockets[match_id] = {}
    sockets[match_id][me] = ws
    match = matches[match_id]
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
                else:
                    raise ValueError("Unknown action.")
            except (ValueError, KeyError) as error:
                await ws.send_json({"type": "ACTION_REJECTED", "reason": str(error)})
                continue
            await broadcast(match_id)
            if match.winner is not None:
                await save_result(ws, match_id, match)
                matches.pop(match_id, None)
    except WebSocketDisconnect:
        del sockets[match_id][me]
