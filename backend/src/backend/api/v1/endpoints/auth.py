import re
import secrets
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from backend.api.cookies import set_session_cookies, set_two_factor_cookie
from backend.api.dependencies.auth import (
    cookie_scheme,
    get_session_store,
    get_two_factor_store,
    verify_csrf,
)
from backend.api.v1.endpoints.two_factor import start_login_challenge
from backend.core.config import settings
from backend.core.email import EmailSender, get_email_sender
from backend.core.exceptions import (
    BadGatewayException,
    BadRequestException,
    ServiceUnavailableException,
    UnauthorizedException,
    UserAlreadyExistsException,
)
from backend.core.security import hash_password, verify_password
from backend.core.session_store import RedisSessionStore
from backend.core.two_factor import TwoFactorStore
from backend.db.session import get_db
from backend.db.uow import UnitOfWork
from backend.models.user import OAuthProvider, User
from backend.repositories.user import UserRepository
from backend.schemas.auth import LoginRequest
from backend.schemas.two_factor import TwoFactorChallengeResponse
from backend.schemas.user import UserCreateRequest, UserResponse
from fastapi import APIRouter, Cookie, Depends, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["Auth"])


async def _google_username(
    user_repo: UserRepository,
    email: str,
    google_id: str,
) -> str:
    local_part = email.split("@", maxsplit=1)[0].lower()
    base = re.sub(r"[^a-z0-9_]", "_", local_part).strip("_") or "google_user"
    candidate = f"{base[:23]}_{google_id[:8]}"
    if not await user_repo.get_by_username(candidate):
        return candidate

    return f"{base[:23]}_{secrets.token_hex(4)}"


def _with_query_param(url: str, key: str, value: str) -> str:
    parts = urlsplit(url)
    query = urlencode([*parse_qsl(parts.query), (key, value)])
    return urlunsplit(parts._replace(query=query))


@router.post(
    "/login",
    response_model=UserResponse,
    responses={
        status.HTTP_202_ACCEPTED: {
            "model": TwoFactorChallengeResponse,
            "description": "Password accepted; a code was emailed. "
            "Finish with POST /auth/2fa/verify",
        }
    },
)
async def login(
    credentials: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    session_store: RedisSessionStore = Depends(get_session_store),
    two_factor_store: TwoFactorStore = Depends(get_two_factor_store),
    email_sender: EmailSender = Depends(get_email_sender),
) -> UserResponse | JSONResponse:
    """Authenticate a user and create a new session.

    Users with 2FA enabled are emailed a code and get a 202 challenge instead.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(credentials.email)

    if (
        not user
        or not user.password_hash
        or not verify_password(credentials.password, user.password_hash)
    ):
        raise UnauthorizedException("Invalid email or password")

    if user.two_factor_enabled:
        token, body = await start_login_challenge(user, two_factor_store, email_sender)
        challenge = JSONResponse(
            status_code=status.HTTP_202_ACCEPTED, content=body.model_dump()
        )
        set_two_factor_cookie(challenge, token)
        return challenge

    session_id = await session_store.create_session(
        user_id=user.id,
    )
    set_session_cookies(response, session_id)

    return UserResponse.model_validate(user)


@router.get("/google", include_in_schema=False)
async def google_login(
    session_store: RedisSessionStore = Depends(get_session_store),
) -> RedirectResponse:
    """Start Google's authorization-code flow."""
    if not settings.GOOGLE_CLIENT_ID:
        raise ServiceUnavailableException("Google authentication is not configured")

    state = secrets.token_urlsafe(32)
    await session_store.create_oauth_state(
        state,
        ttl_seconds=settings.GOOGLE_OAUTH_STATE_TTL_SECONDS,
    )
    query = urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
    )
    response = RedirectResponse(
        f"https://accounts.google.com/o/oauth2/v2/auth?{query}",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    response.set_cookie(
        key="google_oauth_state",
        value=state,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=settings.GOOGLE_OAUTH_STATE_TTL_SECONDS,
    )
    return response


@router.get("/google/callback", include_in_schema=False)
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    state_cookie: str | None = Cookie(None, alias="google_oauth_state"),
    session_store: RedisSessionStore = Depends(get_session_store),
    two_factor_store: TwoFactorStore = Depends(get_two_factor_store),
    email_sender: EmailSender = Depends(get_email_sender),
) -> RedirectResponse:
    """Exchange Google's code, create or find the user, and start a session."""
    if error:
        raise BadRequestException("Google authentication was cancelled")
    if (
        not code
        or not state
        or not state_cookie
        or not secrets.compare_digest(state, state_cookie)
        or not await session_store.consume_oauth_state(state)
    ):
        raise BadRequestException("Invalid or expired Google authentication state")
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ServiceUnavailableException("Google authentication is not configured")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                },
            )
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")
            if not access_token:
                raise BadGatewayException("Google did not return an access token")

            profile_response = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            profile_response.raise_for_status()
            profile = profile_response.json()
    except httpx.HTTPError as exc:
        raise BadGatewayException("Could not complete Google authentication") from exc

    google_id = profile.get("sub")
    email = profile.get("email")
    if (
        not isinstance(google_id, str)
        or not isinstance(email, str)
        or not profile.get("email_verified")
    ):
        raise BadRequestException(
            "Google account does not provide a verified email address"
        )

    async with UnitOfWork() as uow:
        user = await uow.users.get_by_oauth_id(google_id)
        if user is None:
            existing_user = await uow.users.get_by_email(email)
            if existing_user:
                raise UserAlreadyExistsException(
                    "An account with this email already exists. Log in with your password first."
                )

            user = await uow.users.create(
                User(
                    username=await _google_username(uow.users, email, google_id),
                    email=email,
                    password_hash=None,
                    oauth_provider=OAuthProvider.GOOGLE,
                    oauth_id=google_id,
                    avatar_url=profile.get("picture"),
                )
            )
        await uow.commit()
        await uow.session.refresh(user)

    if user.two_factor_enabled:
        # The frontend sees ?two_factor=required and asks for the emailed code.
        token, _ = await start_login_challenge(user, two_factor_store, email_sender)
        response = RedirectResponse(
            _with_query_param(
                settings.GOOGLE_FRONTEND_REDIRECT_URI, "two_factor", "required"
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
        set_two_factor_cookie(response, token)
        response.delete_cookie("google_oauth_state", path="/")
        return response

    session_id = await session_store.create_session(user.id)
    response = RedirectResponse(
        settings.GOOGLE_FRONTEND_REDIRECT_URI,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    set_session_cookies(response, session_id)
    response.delete_cookie("google_oauth_state", path="/")
    return response


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


@router.post(
    "/refresh-session",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
async def refresh_session(
    response: Response,
    session_id: str | None = Depends(cookie_scheme),
    session_store: RedisSessionStore = Depends(get_session_store),
) -> None:
    """Refresh the current session and extend the browser cookie lifetimes."""
    if not session_id:
        raise UnauthorizedException("No active session to refresh.")

    if not await session_store.refresh_session(session_id):
        raise UnauthorizedException("Session expired or invalid")

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=settings.SESSION_TTL_SECONDS,
    )


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_create: UserCreateRequest,
) -> UserResponse:
    """Register a new user"""
    async with UnitOfWork() as uow:
        existing_email = await uow.users.get_by_email(user_create.email)
        if existing_email:
            raise UserAlreadyExistsException("Email already registered.")

        existing_username = await uow.users.get_by_username(user_create.username)
        if existing_username:
            raise UserAlreadyExistsException("Username already taken.")

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
