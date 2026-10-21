from backend.api.dependencies.auth import get_current_user, get_session_store
from backend.core.security import hash_password
from backend.core.session_store import RedisSessionStore
from backend.db.uow import UnitOfWork
from backend.models.user import User
from backend.schemas.user import UserCreateRequest, UserResponse
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Retrieve the currently authenticated user's information."""
    return UserResponse.model_validate(current_user)
