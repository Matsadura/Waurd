"""The match socket: /api/v1/ws/matches/{match_id}.

Checks the Origin header and the session cookie, then hands every message to
the MatchHub (backend.live.hub). Messages are JSON { type, data }; replies
carry { type, data, seq }.
"""

import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from backend.core.config import settings
from backend.core.identifiers import user_id_to_bytes, user_id_to_string
from backend.core.session_store import RedisSessionStore
from backend.live.hub import MatchAccessError, MatchHub

router = APIRouter(tags=["Match socket"])


async def _user_id(websocket: WebSocket) -> str | None:
    session_id = websocket.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_id:
        return None
    store = RedisSessionStore(
        websocket.app.state.redis, ttl_seconds=settings.SESSION_TTL_SECONDS
    )
    session = await store.get_session(session_id)
    if not session:
        return None
    return user_id_to_string(user_id_to_bytes(session["user_id"]))


@router.websocket("/ws/matches/{match_id}")
async def match_socket(websocket: WebSocket, match_id: str) -> None:
    origin = websocket.headers.get("origin")
    if origin is not None and origin not in settings.CORS_ORIGINS:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    user_id = await _user_id(websocket)
    if user_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        match_id = str(uuid.UUID(match_id))
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    hub: MatchHub = websocket.app.state.match_hub
    await websocket.accept()
    try:
        connection = await hub.connect(match_id, user_id, websocket.send_json)
    except MatchAccessError as error:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=str(error))
        return

    try:
        while True:
            text = await websocket.receive_text()
            try:
                message = json.loads(text)
            except ValueError:
                await websocket.send_json(
                    {
                        "type": "ERROR",
                        "data": {"code": "INVALID_JSON", "detail": "Send JSON."},
                    }
                )
                continue
            await hub.receive(connection, message)
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(connection)
