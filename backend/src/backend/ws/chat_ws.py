"""Chat over one WebSocket per user: global, direct and match messages."""

import logging
import uuid

from backend.core.config import settings
from backend.core.identifiers import user_id_to_bytes, user_id_to_string
from backend.db.session import async_session_maker
from backend.models.chat import ChannelType, ChatMessage
from backend.models.friendship import FriendshipStatus
from backend.models.user import User
from backend.repositories.friendship import FriendshipRepository
from backend.repositories.match import MatchRepository
from backend.repositories.user import UserRepository
from backend.schemas.chat import chat_message_response
from backend.ws.match_ws import user_id_from_cookie
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("uvicorn.error")

router = APIRouter()
MAX_LENGTH = 500
sockets: dict[str, set[WebSocket]] = {}  # user id -> open chat sockets, one per tab


def text_field(message: object, name: str) -> str:
    value = message.get(name) if isinstance(message, dict) else None
    if not isinstance(value, str):
        raise ValueError(f'"{name}" must be a string.')
    return value


async def send(user: User, message: object) -> None:
    """Save one chat message and deliver it to everyone who should see it."""
    try:
        channel = ChannelType(text_field(message, "type"))
    except ValueError:
        raise ValueError('"type" must be GLOBAL, DIRECT or MATCH.') from None
    text = text_field(message, "text").strip()
    if not text:
        raise ValueError("The message is empty.")
    if len(text) > MAX_LENGTH:
        raise ValueError(f"Messages are at most {MAX_LENGTH} characters.")

    row = ChatMessage(sender_id=user.id, channel_type=channel, message_content=text)
    async with async_session_maker() as db:
        if channel == ChannelType.GLOBAL:
            recipients = list(sockets)  # everyone online
        elif channel == ChannelType.DIRECT:
            receiver = await UserRepository(db).get_by_id(
                user_id_to_bytes(text_field(message, "to"))
            )
            if receiver is None or receiver.id == user.id:
                raise ValueError("No such player.")
            link = await FriendshipRepository(db).get_by_users(user.id, receiver.id)
            if link is not None and link.status == FriendshipStatus.BLOCKED:
                raise ValueError("You can't message this player.")
            row.receiver_id = receiver.id
            recipients = [user_id_to_string(user.id), user_id_to_string(receiver.id)]
        else:
            match_id = uuid.UUID(text_field(message, "match_id")).bytes
            match = await MatchRepository(db).get_match_by_id(match_id)
            if match is None or user.id not in (match.player1_id, match.player2_id):
                raise ValueError("You're not a player in this match.")
            row.match_id = match.id
            recipients = [
                user_id_to_string(p) for p in (match.player1_id, match.player2_id) if p
            ]
        db.add(row)
        await db.commit()

    out = {
        "type": "CHAT_MESSAGE",
        **chat_message_response(row, user.username).model_dump(mode="json"),
    }
    for recipient in set(recipients):
        for socket in list(sockets.get(recipient, ())):
            try:
                await socket.send_json(out)
            except (WebSocketDisconnect, RuntimeError):
                pass  # that socket's own loop notices the drop and cleans up


@router.websocket("/chat")
async def chat(ws: WebSocket) -> None:
    origin = ws.headers.get("origin")
    if origin not in settings.CORS_ORIGINS:
        logger.info("Chat WS rejected: origin %r is not allowed", origin)
        await ws.close()
        return

    user_id = await user_id_from_cookie(ws)
    if user_id is None:
        logger.info("Chat WS rejected: no valid session cookie")
        await ws.close()
        return
    async with async_session_maker() as db:
        user = await UserRepository(db).get_by_id(user_id_to_bytes(user_id))
    if user is None:
        await ws.close()
        return

    await ws.accept()
    user_id = user_id_to_string(user.id)  # the same spelling the recipients use
    sockets.setdefault(user_id, set()).add(ws)
    try:
        while True:
            try:
                await send(user, await ws.receive_json())
            except (ValueError, KeyError, TypeError) as error:
                await ws.send_json({"type": "CHAT_REJECTED", "reason": str(error)})
    except WebSocketDisconnect:
        pass
    finally:
        mine = sockets.get(user_id, set())
        mine.discard(ws)
        if not mine:
            sockets.pop(user_id, None)
