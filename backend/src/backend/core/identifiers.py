import uuid

from backend.core.exceptions import BadRequestException


def user_id_to_string(user_id: bytes | str | uuid.UUID) -> str:
    if isinstance(user_id, bytes):
        return str(uuid.UUID(bytes=user_id))
    return str(user_id)


def user_id_to_bytes(user_id: bytes | str | uuid.UUID) -> bytes:
    if isinstance(user_id, bytes):
        return user_id
    return uuid.UUID(str(user_id)).bytes


def parse_user_id(user_id: str) -> bytes:
    try:
        return user_id_to_bytes(user_id)
    except ValueError as exc:
        raise BadRequestException("Invalid user identifier") from exc
