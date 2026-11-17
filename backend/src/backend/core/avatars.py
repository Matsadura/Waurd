"""Avatar files on disk, with a built-in default image."""

from pathlib import Path

from backend.core.config import settings
from backend.core.identifiers import user_id_to_string

DEFAULT_AVATAR = (
    Path(__file__).resolve().parent.parent / "static" / "default-avatar.svg"
)

# Detected from the file's first bytes, never from the client's filename or
# Content-Type, so a disguised file cannot be stored as an image.
_SIGNATURES: list[tuple[bytes, str, str]] = [
    (b"\x89PNG\r\n\x1a\n", "png", "image/png"),
    (b"\xff\xd8\xff", "jpg", "image/jpeg"),
    (b"GIF87a", "gif", "image/gif"),
    (b"GIF89a", "gif", "image/gif"),
]
MEDIA_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}


def detect_image_type(data: bytes) -> str | None:
    """Return the file extension for a supported image, else None."""
    for signature, extension, _ in _SIGNATURES:
        if data.startswith(signature):
            return extension
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def avatar_dir() -> Path:
    return Path(settings.MEDIA_DIR) / "avatars"


def find_avatar(user_id: bytes | str) -> Path | None:
    """Return the uploaded avatar for a user, if there is one."""
    name = user_id_to_string(user_id)
    for extension in MEDIA_TYPES:
        path = avatar_dir() / f"{name}.{extension}"
        if path.is_file():
            return path
    return None


def delete_avatar(user_id: bytes | str) -> None:
    name = user_id_to_string(user_id)
    for extension in MEDIA_TYPES:
        (avatar_dir() / f"{name}.{extension}").unlink(missing_ok=True)


def save_avatar(user_id: bytes | str, data: bytes, extension: str) -> Path:
    """Replace the user's avatar. Files are named after the user id only."""
    directory = avatar_dir()
    directory.mkdir(parents=True, exist_ok=True)
    delete_avatar(user_id)
    path = directory / f"{user_id_to_string(user_id)}.{extension}"
    path.write_bytes(data)
    return path
