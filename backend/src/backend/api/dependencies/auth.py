# app/api/dependencies/auth.py
import secrets

import redis.asyncio as aioredis
from backend.core.config import settings
from backend.core.session_store import RedisSessionStore
from backend.db.session import get_db
from backend.models.user import User
from backend.repositories.user import UserRepository
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession

cookie_scheme = APIKeyCookie(name=settings.SESSION_COOKIE_NAME, auto_error=False)


# Shared Redis pool dependency
async def get_redis() -> aioredis.Redis:
    return aioredis.from_url(str(settings.REDIS_URL), decode_responses=True)


def get_session_store(redis: aioredis.Redis = Depends(get_redis)) -> RedisSessionStore:
    return RedisSessionStore(redis, ttl_seconds=settings.SESSION_TTL_SECONDS)


async def get_current_user(
    session_id: str | None = Depends(cookie_scheme),
    session_store: RedisSessionStore = Depends(get_session_store),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate the HTTP session cookie and resolve the authenticated User entity."""
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    session_data = await session_store.get_session(session_id)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(session_data["user_id"])
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User inactive or not found",
        )

    return user


async def verify_csrf(
    request: Request,
    csrf_token_header: str | None = Header(None, alias="X-CSRF-Token"),
    csrf_token_cookie: str | None = Cookie(None, alias=settings.CSRF_COOKIE_NAME),
) -> None:
    """Double-Submit Cookie CSRF defense for state-mutating requests."""
    if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        return

    if not csrf_token_header or not csrf_token_cookie:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing",
        )

    # Constant-time comparison prevents timing attacks
    if not secrets.compare_digest(csrf_token_header, csrf_token_cookie):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )
