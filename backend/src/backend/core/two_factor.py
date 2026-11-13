"""One-time verification codes for email-based two-factor authentication."""

import enum
import hmac
import secrets

import redis.asyncio as aioredis

from backend.core.identifiers import user_id_to_string

CODE_DIGITS = 6


def generate_code() -> str:
    return f"{secrets.randbelow(10**CODE_DIGITS):0{CODE_DIGITS}d}"


def mask_email(email: str) -> str:
    """Hint at the inbox a code went to without revealing the whole address."""
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


class CodeCheck(enum.Enum):
    VALID = "valid"
    WRONG = "wrong"
    LOCKED = "locked"
    MISSING = "missing"


class TwoFactorAction(str, enum.Enum):
    ENABLE = "enable"
    DISABLE = "disable"


class TwoFactorStore:
    """Codes live in Redis only, so they expire on their own.

    Keys use their own prefix so session scans over ``session:*`` never see them.
    """

    prefix = "2fa:"

    def __init__(
        self,
        redis_client: aioredis.Redis,
        *,
        code_ttl_seconds: int,
        max_attempts: int,
        resend_cooldown_seconds: int,
    ) -> None:
        self.redis = redis_client
        self.code_ttl = code_ttl_seconds
        self.max_attempts = max_attempts
        self.resend_cooldown = resend_cooldown_seconds

    def _key(self, kind: str, value: str) -> str:
        return f"{self.prefix}{kind}:{value}"

    async def claim_send_slot(self, user_id: bytes | str) -> bool:
        """Allow one email per cooldown window; False means wait."""
        key = self._key("cooldown", user_id_to_string(user_id))
        return bool(await self.redis.set(key, "1", nx=True, ex=self.resend_cooldown))

    async def release_send_slot(self, user_id: bytes | str) -> None:
        """Give the slot back when the email could not be sent."""
        await self.redis.delete(self._key("cooldown", user_id_to_string(user_id)))

    async def _store(self, key: str, fields: dict[str, str]) -> None:
        await self.redis.delete(key)
        await self.redis.hset(key, mapping={**fields, "attempts": "0"})
        await self.redis.expire(key, self.code_ttl)

    async def _check(self, key: str, code: str) -> tuple[CodeCheck, dict[str, str]]:
        data = await self.redis.hgetall(key)
        if not data.get("code"):
            await self.redis.delete(key)
            return CodeCheck.MISSING, {}

        # Count before comparing so parallel guesses cannot exceed the limit.
        if await self.redis.hincrby(key, "attempts", 1) > self.max_attempts:
            await self.redis.delete(key)
            return CodeCheck.LOCKED, {}

        if not hmac.compare_digest(data["code"], code):
            return CodeCheck.WRONG, {}

        # Only the request that actually deletes the key wins, so a code
        # cannot be used twice by concurrent requests.
        if not await self.redis.delete(key):
            return CodeCheck.MISSING, {}
        return CodeCheck.VALID, data

    # Login challenge: issued after the password or Google step succeeds.
    async def create_login_challenge(self, user_id: bytes | str, code: str) -> str:
        token = secrets.token_urlsafe(32)
        await self._store(
            self._key("login", token),
            {"user_id": user_id_to_string(user_id), "code": code},
        )
        return token

    async def delete_login_challenge(self, token: str) -> None:
        await self.redis.delete(self._key("login", token))

    async def check_login_code(
        self, token: str, code: str
    ) -> tuple[CodeCheck, str | None]:
        result, data = await self._check(self._key("login", token), code)
        return result, data.get("user_id")

    # Codes that confirm turning 2FA on or off for a signed-in user.
    async def create_action_code(
        self, user_id: bytes | str, action: TwoFactorAction, code: str
    ) -> None:
        await self._store(
            self._key("action", f"{user_id_to_string(user_id)}:{action.value}"),
            {"code": code},
        )

    async def delete_action_code(
        self, user_id: bytes | str, action: TwoFactorAction
    ) -> None:
        await self.redis.delete(
            self._key("action", f"{user_id_to_string(user_id)}:{action.value}")
        )

    async def check_action_code(
        self, user_id: bytes | str, action: TwoFactorAction, code: str
    ) -> CodeCheck:
        result, _ = await self._check(
            self._key("action", f"{user_id_to_string(user_id)}:{action.value}"), code
        )
        return result
