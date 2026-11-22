from backend.game.models import Match
from backend.game.rules import cast_word, pass_turn, start_turn
from backend.game.setup import load_words, new_match
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pathlib import Path

router = APIRouter()
DATA_DIR = Path(__file__).parent.parent / "data"
WORDS = load_words(DATA_DIR / "enable1.txt")
matches: dict[str, Match] = {}
sockets: dict[int, list[WebSocket]] = {}


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


@router.websocket("/matches/{match_id}/{me}")
async def play(ws: WebSocket, match_id: str, me: int):
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
    except WebSocketDisconnect:
        del sockets[match_id][me]
