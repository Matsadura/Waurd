from datetime import datetime

from pydantic import BaseModel

from backend.core.identifiers import user_id_to_string
from backend.models.chat import ChannelType, ChatMessage


class ChatMessageResponse(BaseModel):
    id: int
    channel: ChannelType
    sender_id: str
    sender_username: str
    receiver_id: str | None = None  # DIRECT only
    match_id: str | None = None  # MATCH only
    text: str
    created_at: datetime


def chat_message_response(
    message: ChatMessage, sender_username: str
) -> ChatMessageResponse:
    """One message, the same shape over HTTP and the chat socket."""
    return ChatMessageResponse(
        id=message.id,
        channel=message.channel_type,
        sender_id=user_id_to_string(message.sender_id),
        sender_username=sender_username,
        receiver_id=message.receiver_id and user_id_to_string(message.receiver_id),
        match_id=message.match_id and user_id_to_string(message.match_id),
        text=message.message_content,
        created_at=message.created_at,
    )
