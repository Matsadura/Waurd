import hashlib
from uuid import UUID

from backend.api.dependencies.auth import get_current_user, get_session_store
from backend.core.avatars import (
    DEFAULT_AVATAR,
    MEDIA_TYPES,
    delete_avatar,
    detect_image_type,
    find_avatar,
    save_avatar,
)
from backend.core.config import settings
from backend.core.exceptions import (
    AppException,
    BadRequestException,
    EntityNotFoundException,
    ForbiddenException,
    UserAlreadyExistsException,
)
from backend.core.identifiers import user_id_to_bytes, user_id_to_string
from backend.core.security import hash_password, verify_password
from backend.core.session_store import RedisSessionStore
from backend.db.uow import UnitOfWork
from backend.models.match import MatchStatus
from backend.models.user import User, UserRole
from backend.schemas.match import MatchResponse
from backend.schemas.pagination import PaginatedResponse
from backend.schemas.user import UserResponse, UserStatsResponse, UserUpdateRequest
from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse

router = APIRouter(prefix="/users", tags=["Users"])

# Uploaded files are served with their detected type only.
IMAGE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "private, max-age=300",
}


def _can_view(current_user: User, user_id: UUID) -> bool:
    """Users see their own data; game masters see everyone's."""
    return user_id.bytes == current_user.id or current_user.role == UserRole.GAME_MASTER


async def _set_avatar_url(
    uow: UnitOfWork, user_id: bytes, avatar_url: str | None
) -> UserResponse:
    async with uow:
        user = await uow.users.get_by_id(user_id)
        if user is None:
            raise EntityNotFoundException("User not found")
        user = await uow.users.update(user, {"avatar_url": avatar_url})
        await uow.commit()
        await uow.session.refresh(user)
        return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Retrieve the currently authenticated user's information."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    user_update: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    session_store: RedisSessionStore = Depends(get_session_store),
    uow: UnitOfWork = Depends(),
) -> UserResponse:
    """Update the currently authenticated user's information."""
    attributes = {}
    if user_update.password:
        # Google-only accounts have no password yet, so they can set one directly.
        if current_user.password_hash and not (
            user_update.current_password
            and verify_password(
                user_update.current_password, current_user.password_hash
            )
        ):
            raise BadRequestException("Current password is incorrect.")
        attributes["password_hash"] = hash_password(user_update.password)

    # Update other fields if provided
    if user_update.username:
        attributes["username"] = user_update.username
    if user_update.email:
        attributes["email"] = user_update.email
    if user_update.avatar_url:
        attributes["avatar_url"] = user_update.avatar_url
    # Read before the update; an unchanged email in a resent form keeps the session.
    signs_out = "password_hash" in attributes or (
        user_update.email is not None and user_update.email != current_user.email
    )

    async with uow:
        user = await uow.users.get_by_id(current_user.id)
        if user is None:
            raise EntityNotFoundException("User not found")
        if (
            user_update.username
            and user_update.username != user.username
            and await uow.users.get_by_username(user_update.username)
        ):
            raise UserAlreadyExistsException("Username already taken.")
        if (
            user_update.email
            and user_update.email != user.email
            and await uow.users.get_by_email(user_update.email)
        ):
            raise UserAlreadyExistsException("Email already registered.")
        user = await uow.users.update(user, attributes)
        await uow.commit()
        await uow.users.session.refresh(user)
        response = UserResponse.model_validate(user)

    # A new password or email signs out every session; a new username does not.
    if signs_out:
        await session_store.invalidate_session(current_user.id)

    return response


@router.put("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(..., description="PNG, JPEG, WebP or GIF image"),
    current_user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(),
) -> UserResponse:
    """Upload or replace the current user's avatar."""
    limit = settings.AVATAR_MAX_BYTES
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise AppException(
            f"Avatar must be at most {limit // (1024 * 1024)} MB.",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    extension = detect_image_type(data)
    if extension is None:
        raise BadRequestException("Avatar must be a PNG, JPEG, WebP or GIF image.")

    save_avatar(current_user.id, data, extension)
    # The version changes with the image, so browsers drop their cached copy.
    version = hashlib.sha256(data).hexdigest()[:12]
    avatar_url = (
        f"{settings.API_V1_STR}/users/{user_id_to_string(current_user.id)}"
        f"/avatar?v={version}"
    )
    return await _set_avatar_url(uow, current_user.id, avatar_url)


@router.delete("/me/avatar", response_model=UserResponse)
async def remove_avatar(
    current_user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(),
) -> UserResponse:
    """Remove the current user's avatar; the default image is shown instead."""
    delete_avatar(current_user.id)
    return await _set_avatar_url(uow, current_user.id, None)


@router.get(
    "/{user_id}/avatar",
    response_class=Response,
    responses={
        200: {
            "content": {media: {} for media in [*MEDIA_TYPES.values(), "image/svg+xml"]}
        },
        307: {"description": "Redirect to an external avatar, such as Google's"},
    },
)
async def get_avatar(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(),
) -> Response:
    """Any signed-in user can load any avatar; a default image fills the gap."""
    async with uow:
        user = await uow.users.get_by_id(user_id.bytes)
    if user is None:
        raise EntityNotFoundException("User not found")

    if user.avatar_url and user.avatar_url.startswith(("https://", "http://")):
        return RedirectResponse(user.avatar_url)

    path = find_avatar(user.id)
    if path is not None:
        return FileResponse(
            path,
            media_type=MEDIA_TYPES[path.suffix.lstrip(".")],
            headers=IMAGE_HEADERS,
        )
    return FileResponse(
        DEFAULT_AVATAR, media_type="image/svg+xml", headers=IMAGE_HEADERS
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(),
) -> UserResponse:
    """Retrieve a user's information by their unique identifier."""
    async with uow:
        if not _can_view(current_user, user_id):
            raise ForbiddenException(
                "You do not have permission to access this user's information."
            )
        user = await uow.users.get_by_id(user_id_to_bytes(user_id))
        if user is None:
            raise EntityNotFoundException("User not found")
        return UserResponse.model_validate(user)


@router.get("/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(),
) -> UserStatsResponse:
    """Retrieve a user's statistics by their unique identifier."""
    async with uow:
        if not _can_view(current_user, user_id):
            raise ForbiddenException(
                "You do not have permission to access this user's statistics."
            )
        user_stats = await uow.user_stats.get_by_user_id(user_id.bytes)
        if user_stats is None:
            raise EntityNotFoundException("User statistics not found")
        return UserStatsResponse.model_validate(user_stats)


@router.get("/{user_id}/matches", response_model=PaginatedResponse[MatchResponse])
async def get_user_matches(
    user_id: UUID,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    match_status: MatchStatus | None = Query(
        None, alias="status", description="Only matches in this status, e.g. FINISHED"
    ),
    current_user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(),
) -> PaginatedResponse[MatchResponse]:
    """Retrieve a paginated list of matches for a specific user, with both
    players' usernames. ?status=FINISHED keeps only completed matches."""
    async with uow:
        if not _can_view(current_user, user_id):
            raise ForbiddenException(
                "You do not have permission to access this user's matches."
            )
        skip = (page - 1) * size
        matches, total = await uow.matches.get_matches_for_user(
            user_id.bytes, skip=skip, limit=size, status=match_status
        )
        items = [MatchResponse.model_validate(match) for match in matches]
        return PaginatedResponse.create(items=items, total=total, page=page, size=size)
