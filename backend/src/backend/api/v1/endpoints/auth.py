import secrets

from backend.api.dependencies.auth import (
    cookie_scheme,
    get_current_user,
    get_session_store,
    verify_csrf,
)
from backend.core.config import settings
from backend.core.security import hash_password, verify_password
from backend.core.session_store import RedisSessionStore
from backend.db.session import get_db
from backend.db.uow import UnitOfWork
from backend.models.user import User
from backend.repositories.user import UserRepository
from backend.schemas.auth import LoginRequest
from backend.schemas.user import UserCreateRequest, UserResponse
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=UserResponse)
async def login(
    credentials: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    session_store: RedisSessionStore = Depends(get_session_store),
) -> UserResponse:
    """Authenticate a user and create a new session."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(credentials.email)

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    session_id = await session_store.create_session(
        user_id=user.id,
    )
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=settings.SESSION_TTL_SECONDS,
    )

    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=secrets.token_urlsafe(32),
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=settings.SESSION_TTL_SECONDS,
    )

    return UserResponse.model_validate(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
async def logout(
    response: Response,
    session_id: str | None = Depends(cookie_scheme),
    session_store: RedisSessionStore = Depends(get_session_store),
) -> None:
    """Invalidate the current session and clear cookies."""
    if session_id:
        await session_store.delete_session(session_id)

    response.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(key=settings.CSRF_COOKIE_NAME, path="/")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Retrieve the currently authenticated user's information."""
    return UserResponse.model_validate(current_user)

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_create: UserCreateRequest,
) -> UserResponse:
    """Register a new user"""
    async with UnitOfWork() as uow:
        existing_user = await uow.users.get_by_email(user_create.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered.",
            )

        new_user = await uow.users.create(
            User(
                username=user_create.username,
                email=user_create.email,
                password_hash=hash_password(user_create.password),
            )
        )
        await uow.commit()
        await uow.session.refresh(new_user)

    return UserResponse.model_validate(new_user)