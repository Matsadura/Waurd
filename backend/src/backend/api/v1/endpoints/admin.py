from uuid import UUID

from backend.api.dependencies.auth import get_session_store, require_game_master
from backend.core.avatars import delete_avatar
from backend.core.exceptions import (
    BadRequestException,
    EntityNotFoundException,
    UserAlreadyExistsException,
)
from backend.core.session_store import RedisSessionStore
from backend.db.uow import UnitOfWork
from backend.models.user import User
from backend.schemas.admin import (
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
)
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_

# Every route needs a game master; the router adds CSRF on top.
router = APIRouter(
    prefix="/admin/users",
    tags=["Admin"],
    dependencies=[Depends(require_game_master)],
)


async def _get_user(uow: UnitOfWork, user_id: UUID) -> User:
    user = await uow.users.get_by_id(user_id.bytes)
    if user is None:
        raise EntityNotFoundException("User not found")
    return user


@router.get("", response_model=AdminUserListResponse)
async def list_users(
    q: str | None = Query(
        None, max_length=255, description="Username or email contains"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    uow: UnitOfWork = Depends(),
) -> AdminUserListResponse:
    """List users, newest first."""
    filters = []
    if q:
        pattern = f"%{q}%"
        filters.append(or_(User.username.ilike(pattern), User.email.ilike(pattern)))

    async with uow:
        users = await uow.users.list(
            *filters,
            order_by=[User.created_at.desc(), User.username],
            limit=limit,
            offset=offset,
        )
        total = await uow.users.count(*filters)
        return AdminUserListResponse(
            users=[AdminUserResponse.model_validate(user) for user in users],
            total=total,
        )


@router.get("/{user_id}", response_model=AdminUserResponse)
async def get_user(user_id: UUID, uow: UnitOfWork = Depends()) -> AdminUserResponse:
    async with uow:
        return AdminUserResponse.model_validate(await _get_user(uow, user_id))


@router.patch("/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: UUID,
    payload: AdminUserUpdateRequest,
    game_master: User = Depends(require_game_master),
    uow: UnitOfWork = Depends(),
) -> AdminUserResponse:
    """Edit a user's profile or role."""
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)

    async with uow:
        user = await _get_user(uow, user_id)
        # Keeps at least one game master: nobody can demote themselves.
        if "role" in changes and user.id == game_master.id:
            raise BadRequestException("You cannot change your own role")
        if changes.get(
            "username", user.username
        ) != user.username and await uow.users.get_by_username(changes["username"]):
            raise UserAlreadyExistsException("Username already taken.")
        if changes.get(
            "email", user.email
        ) != user.email and await uow.users.get_by_email(changes["email"]):
            raise UserAlreadyExistsException("Email already registered.")

        user = await uow.users.update(user, changes)
        await uow.commit()
        await uow.session.refresh(user)
        return AdminUserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    game_master: User = Depends(require_game_master),
    session_store: RedisSessionStore = Depends(get_session_store),
    uow: UnitOfWork = Depends(),
) -> None:
    """Delete a user with everything that belongs to them."""
    if user_id.bytes == game_master.id:
        raise BadRequestException("You cannot delete your own account here")

    async with uow:
        await _get_user(uow, user_id)
        # A SQL DELETE lets the database's ON DELETE rules remove friendships,
        # stats and matches, without loading every relationship into memory.
        await uow.users.delete_by_id(user_id.bytes)
        await uow.commit()

    await session_store.invalidate_session(user_id.bytes)
    delete_avatar(user_id.bytes)
