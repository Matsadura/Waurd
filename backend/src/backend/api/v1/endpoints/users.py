from uuid import UUID

from backend.api.dependencies.auth import get_current_user, get_session_store
from backend.core.exceptions import (
    EntityNotFoundException,
    ForbiddenException,
    UserAlreadyExistsException,
)
from backend.core.identifiers import user_id_to_bytes
from backend.core.security import hash_password
from backend.core.session_store import RedisSessionStore
from backend.db.uow import UnitOfWork
from backend.models.user import User
from backend.schemas.match import MatchResponse
from backend.schemas.user import UserResponse, UserStatsResponse, UserUpdateRequest
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/users", tags=["Users"])


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
        attributes["password_hash"] = hash_password(user_update.password)

    # Update other fields if provided
    if user_update.username:
        attributes["username"] = user_update.username
    if user_update.email:
        attributes["email"] = user_update.email
    if user_update.avatar_url:
        attributes["avatar_url"] = user_update.avatar_url

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

    # Invalidate the user's session to force re-authentication
    if attributes:
        await session_store.invalidate_session(current_user.id)

    return response


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(),
) -> UserResponse:
    """Retrieve a user's information by their unique identifier."""
    async with uow:
        if user_id.bytes != current_user.id:
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
        if user_id.bytes != current_user.id:
            raise ForbiddenException(
                "You do not have permission to access this user's statistics."
            )
        user_stats = await uow.user_stats.get_by_user_id(user_id.bytes)
        if user_stats is None:
            raise EntityNotFoundException("User statistics not found")
        return UserStatsResponse.model_validate(user_stats)


@router.get("/{user_id}/matches", response_model=list[MatchResponse])
async def get_user_matches(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(),
) -> list[MatchResponse]:
    """Retrieve a list of matches for a specific user."""
    async with uow:
        if user_id.bytes != current_user.id:
            raise ForbiddenException(
                "You do not have permission to access this user's matches."
            )
        matches = await uow.matches.get_all_matches_for_user(user_id.bytes)
        return [MatchResponse.model_validate(match) for match in matches]
