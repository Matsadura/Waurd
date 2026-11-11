import secrets

from fastapi import Response

from backend.core.config import settings


def set_session_cookies(response: Response, session_id: str) -> None:
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


def set_two_factor_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.TWO_FACTOR_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=settings.TWO_FACTOR_CODE_TTL_SECONDS,
    )


def clear_two_factor_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.TWO_FACTOR_COOKIE_NAME, path="/")
