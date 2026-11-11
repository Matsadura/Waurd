"""Outgoing email through SMTP (Gmail by default) using fastapi-mail."""

import logging
from functools import lru_cache

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors

from backend.core.config import settings
from backend.core.exceptions import BadGatewayException, ServiceUnavailableException
from backend.core.two_factor import TwoFactorAction

logger = logging.getLogger("uvicorn.error")

LOGIN = "login"
SUBJECTS = {
    LOGIN: "Your Waurd login code",
    TwoFactorAction.ENABLE: "Confirm two-factor authentication for Waurd",
    TwoFactorAction.DISABLE: "Confirm turning off two-factor authentication",
}
INTROS = {
    LOGIN: "Use this code to finish logging in to Waurd:",
    TwoFactorAction.ENABLE: "Use this code to turn on two-factor authentication:",
    TwoFactorAction.DISABLE: "Use this code to turn off two-factor authentication:",
}


class EmailSender:
    def __init__(self, mailer: FastMail | None) -> None:
        self.mailer = mailer

    @property
    def is_configured(self) -> bool:
        return self.mailer is not None

    async def send_code(
        self, recipient: str, code: str, purpose: str | TwoFactorAction
    ) -> None:
        if self.mailer is None:
            raise ServiceUnavailableException("Email delivery is not configured")

        minutes = settings.TWO_FACTOR_CODE_TTL_SECONDS // 60
        body = (
            f"{INTROS[purpose]}\n\n"
            f"    {code}\n\n"
            f"It expires in {minutes} minutes. If you did not request it, "
            "someone may know your password: change it."
        )
        message = MessageSchema(
            subject=SUBJECTS[purpose],
            recipients=[recipient],
            body=body,
            subtype=MessageType.plain,
        )
        await self._send(message)

    async def send_password_reset_link(self, recipient: str, link: str) -> None:
        if self.mailer is None:
            raise ServiceUnavailableException("Email delivery is not configured")

        minutes = settings.PASSWORD_RESET_TTL_SECONDS // 60
        body = (
            "Open this link to choose a new Waurd password:\n\n"
            f"{link}\n\n"
            f"It works once and expires in {minutes} minutes. If you did not ask "
            "to reset your password, ignore this email. Your password stays the "
            "same."
        )
        await self._send(
            MessageSchema(
                subject="Reset your Waurd password",
                recipients=[recipient],
                body=body,
                subtype=MessageType.plain,
            )
        )

    async def _send(self, message: MessageSchema) -> None:
        try:
            await self.mailer.send_message(message)
        except ConnectionErrors as exc:
            logger.exception("Sending email failed")
            raise BadGatewayException("Could not send the verification email") from exc


@lru_cache
def get_email_sender() -> EmailSender:
    """FastAPI dependency; tests override it with a fake."""
    if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD:
        return EmailSender(None)

    config = ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        # Gmail rejects a From address the account does not own.
        MAIL_FROM=settings.MAIL_FROM or settings.MAIL_USERNAME,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )
    return EmailSender(FastMail(config))
