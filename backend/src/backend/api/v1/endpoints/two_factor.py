from backend.api.cookies import clear_two_factor_cookie, set_session_cookies
from backend.api.dependencies.auth import (
    get_current_user,
    get_session_store,
    get_two_factor_store,
    verify_csrf,
)
from backend.core.config import settings
from backend.core.email import LOGIN, EmailSender, get_email_sender
from backend.core.exceptions import (
    BadRequestException,
    EntityNotFoundException,
    TooManyRequestsException,
    UnauthorizedException,
)
from backend.core.identifiers import user_id_to_bytes
from backend.core.session_store import RedisSessionStore
from backend.core.two_factor import (
    CodeCheck,
    TwoFactorAction,
    TwoFactorStore,
    generate_code,
    mask_email,
)
from backend.db.session import get_db
from backend.db.uow import UnitOfWork
from backend.models.user import User
from backend.repositories.user import UserRepository
from backend.schemas.two_factor import (
    TwoFactorChallengeResponse,
    TwoFactorCodeRequest,
    TwoFactorCodeSendRequest,
    TwoFactorCodeSentResponse,
    TwoFactorStatusResponse,
)
from backend.schemas.user import UserResponse
from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth/2fa", tags=["Two-Factor Auth"])

COOLDOWN_MESSAGE = "A code was sent recently. Wait a minute before asking again."
INVALID_CODE = "Invalid verification code"


async def start_login_challenge(
    user: User,
    store: TwoFactorStore,
    sender: EmailSender,
) -> tuple[str, TwoFactorChallengeResponse]:
    """Email a login code; returns the token for the challenge cookie.

    Used by password and Google login once the first factor has succeeded.
    """
    if not await store.claim_send_slot(user.id):
        raise TooManyRequestsException(COOLDOWN_MESSAGE)

    code = generate_code()
    token = await store.create_login_challenge(user.id, code)
    try:
        await sender.send_code(user.email, code, LOGIN)
    except Exception:
        await store.delete_login_challenge(token)
        await store.release_send_slot(user.id)
        raise

    return token, TwoFactorChallengeResponse(email_hint=mask_email(user.email))


def _raise_for_code(result: CodeCheck, *, locked: str, missing: str) -> None:
    if result is CodeCheck.LOCKED:
        raise TooManyRequestsException(locked)
    if result is CodeCheck.MISSING:
        raise BadRequestException(missing)
    if result is CodeCheck.WRONG:
        raise BadRequestException(INVALID_CODE)


async def _set_enabled(user_id: bytes, enabled: bool) -> None:
    async with UnitOfWork() as uow:
        user = await uow.users.get_by_id(user_id)
        if user is None:
            raise EntityNotFoundException("User not found")
        await uow.users.update(user, {"two_factor_enabled": enabled})
        await uow.commit()


@router.get("", response_model=TwoFactorStatusResponse)
async def get_status(
    current_user: User = Depends(get_current_user),
) -> TwoFactorStatusResponse:
    """Report whether 2FA is enabled for the current user."""
    return TwoFactorStatusResponse(enabled=current_user.two_factor_enabled)


@router.post(
    "/code",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TwoFactorCodeSentResponse,
    dependencies=[Depends(verify_csrf)],
)
async def send_action_code(
    payload: TwoFactorCodeSendRequest,
    current_user: User = Depends(get_current_user),
    store: TwoFactorStore = Depends(get_two_factor_store),
    sender: EmailSender = Depends(get_email_sender),
) -> TwoFactorCodeSentResponse:
    """Email a code that confirms turning 2FA on or off.

    Enabling this way also proves the account's email address is reachable,
    so nobody locks themselves out with a mistyped address.
    """
    enabling = payload.action is TwoFactorAction.ENABLE
    if enabling and current_user.two_factor_enabled:
        raise BadRequestException("Two-factor authentication is already enabled")
    if not enabling and not current_user.two_factor_enabled:
        raise BadRequestException("Two-factor authentication is not enabled")

    if not await store.claim_send_slot(current_user.id):
        raise TooManyRequestsException(COOLDOWN_MESSAGE)

    code = generate_code()
    await store.create_action_code(current_user.id, payload.action, code)
    try:
        await sender.send_code(current_user.email, code, payload.action)
    except Exception:
        await store.delete_action_code(current_user.id, payload.action)
        await store.release_send_slot(current_user.id)
        raise

    return TwoFactorCodeSentResponse(email_hint=mask_email(current_user.email))


@router.post(
    "/enable",
    response_model=TwoFactorStatusResponse,
    dependencies=[Depends(verify_csrf)],
)
async def enable(
    payload: TwoFactorCodeRequest,
    current_user: User = Depends(get_current_user),
    store: TwoFactorStore = Depends(get_two_factor_store),
) -> TwoFactorStatusResponse:
    """Turn on 2FA with a code from POST /auth/2fa/code."""
    if current_user.two_factor_enabled:
        raise BadRequestException("Two-factor authentication is already enabled")

    result = await store.check_action_code(
        current_user.id, TwoFactorAction.ENABLE, payload.code
    )
    _raise_for_code(
        result,
        locked="Too many invalid codes. Request a new code.",
        missing="No verification code requested or it expired. Request a new code.",
    )

    await _set_enabled(current_user.id, True)
    return TwoFactorStatusResponse(enabled=True)


@router.post(
    "/disable",
    response_model=TwoFactorStatusResponse,
    dependencies=[Depends(verify_csrf)],
)
async def disable(
    payload: TwoFactorCodeRequest,
    current_user: User = Depends(get_current_user),
    store: TwoFactorStore = Depends(get_two_factor_store),
) -> TwoFactorStatusResponse:
    """Turn off 2FA with a code from POST /auth/2fa/code."""
    if not current_user.two_factor_enabled:
        raise BadRequestException("Two-factor authentication is not enabled")

    result = await store.check_action_code(
        current_user.id, TwoFactorAction.DISABLE, payload.code
    )
    _raise_for_code(
        result,
        locked="Too many invalid codes. Request a new code.",
        missing="No verification code requested or it expired. Request a new code.",
    )

    await _set_enabled(current_user.id, False)
    return TwoFactorStatusResponse(enabled=False)


@router.post("/verify", response_model=UserResponse)
async def verify_login(
    payload: TwoFactorCodeRequest,
    response: Response,
    challenge_token: str | None = Cookie(None, alias=settings.TWO_FACTOR_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
    session_store: RedisSessionStore = Depends(get_session_store),
    store: TwoFactorStore = Depends(get_two_factor_store),
) -> UserResponse:
    """Finish a login that was answered with a 2FA challenge."""
    if not challenge_token:
        raise UnauthorizedException("Verification code expired. Log in again.")

    result, user_id = await store.check_login_code(challenge_token, payload.code)
    if result is CodeCheck.MISSING:
        raise UnauthorizedException("Verification code expired. Log in again.")
    if result is CodeCheck.LOCKED:
        raise TooManyRequestsException(
            "Too many invalid codes. Log in again to get a new code."
        )
    if result is CodeCheck.WRONG:
        raise UnauthorizedException(INVALID_CODE)

    user = await UserRepository(db).get_by_id(user_id_to_bytes(user_id))
    if not user:
        raise UnauthorizedException("Verification code expired. Log in again.")

    session_id = await session_store.create_session(user.id)
    set_session_cookies(response, session_id)
    clear_two_factor_cookie(response)
    return UserResponse.model_validate(user)
