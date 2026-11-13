import logging

from backend.api.dependencies.auth import get_password_reset_store, get_session_store
from backend.core.config import settings
from backend.core.email import EmailSender, get_email_sender
from backend.core.exceptions import (
    AppException,
    BadRequestException,
    ServiceUnavailableException,
)
from backend.core.identifiers import user_id_to_bytes
from backend.core.password_reset import PasswordResetStore, build_reset_link
from backend.core.security import hash_password
from backend.core.session_store import RedisSessionStore
from backend.db.session import get_db
from backend.db.uow import UnitOfWork
from backend.repositories.user import UserRepository
from backend.schemas.password import (
    PasswordForgotRequest,
    PasswordForgotResponse,
    PasswordResetRequest,
    PasswordResetResponse,
)
from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/auth/password", tags=["Auth"])

INVALID_LINK = "This reset link is invalid or has expired. Request a new one."


async def _send_reset_link(
    sender: EmailSender,
    store: PasswordResetStore,
    user_id: bytes,
    email: str,
    token: str,
) -> None:
    try:
        await sender.send_password_reset_link(
            email, build_reset_link(settings.PASSWORD_RESET_URL, token)
        )
    except AppException:
        # The response is already sent; drop the link so a retry starts clean.
        logger.exception("Password reset email was not sent")
        await store.revoke(user_id)
        await store.release_send_slot(user_id)


@router.post(
    "/forgot",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PasswordForgotResponse,
)
async def forgot_password(
    payload: PasswordForgotRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    store: PasswordResetStore = Depends(get_password_reset_store),
    sender: EmailSender = Depends(get_email_sender),
) -> PasswordForgotResponse:
    """Email a reset link if the address belongs to a password account.

    The answer is the same either way, and the email goes out after the
    response, so neither the body nor its timing reveals who is registered.
    Accounts that only sign in with Google have no password to reset.
    """
    if not sender.is_configured:
        raise ServiceUnavailableException("Email delivery is not configured")

    user = await UserRepository(db).get_by_email(payload.email)
    if user and user.password_hash and await store.claim_send_slot(user.id):
        token = await store.create_token(user.id)
        background_tasks.add_task(
            _send_reset_link, sender, store, user.id, user.email, token
        )

    return PasswordForgotResponse()


@router.post("/reset", response_model=PasswordResetResponse)
async def reset_password(
    payload: PasswordResetRequest,
    session_store: RedisSessionStore = Depends(get_session_store),
    store: PasswordResetStore = Depends(get_password_reset_store),
) -> PasswordResetResponse:
    """Set a new password using the token from the link, then sign out everywhere."""
    user_id = await store.consume_token(payload.token)
    if not user_id:
        raise BadRequestException(INVALID_LINK)

    async with UnitOfWork() as uow:
        user = await uow.users.get_by_id(user_id_to_bytes(user_id))
        if not user or not user.password_hash:
            raise BadRequestException(INVALID_LINK)

        await uow.users.update(
            user, {"password_hash": hash_password(payload.new_password)}
        )
        await uow.commit()

    # Whoever knew the old password must not stay signed in.
    await session_store.invalidate_session(user.id)
    return PasswordResetResponse()
