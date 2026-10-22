from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies.auth import get_current_user, get_session_store
from backend.core.security import hash_password
from backend.core.session_store import RedisSessionStore
from backend.db.uow import UnitOfWork
from backend.models.user import User
from backend.schemas.user import UserCreateRequest, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Retrieve the currently authenticated user's information."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    user_update: UserCreateRequest,
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        user = await uow.users.update(user, attributes)
        await uow.commit()
        await uow.users.session.refresh(user)
        response = UserResponse.model_validate(user)

    # Invalidate the user's session to force re-authentication
    await session_store.invalidate_session(current_user.id)

    return response


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(),
) -> UserResponse:
    """Retrieve a user's information by their unique identifier."""
    async with uow:
        if user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this user's information.",
            )
        user = await uow.users.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return UserResponse.model_validate(user)
