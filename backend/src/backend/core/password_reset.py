"""One-time password reset links, backed by Redis."""

import hashlib
import secrets
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import redis.asyncio as aioredis

from backend.core.identifiers import user_id_to_string


def build_reset_link(base_url: str, token: str) -> str:
    """Add the token to the frontend reset page URL, keeping any query it has."""
    parts = urlsplit(base_url)
    query = urlencode([*parse_qsl(parts.query), ("token", token)])
    return urlunsplit(parts._replace(query=query))


def _digest(token: str) -> str:
    # Only a hash is stored, so reading Redis does not hand out working links.
    return hashlib.sha256(token.encode()).hexdigest()


class PasswordResetStore:
    """Keys use their own prefix so session scans over ``session:*`` never see them."""

    prefix = "password-reset:"

    def __init__(
        self,
        redis_client: aioredis.Redis,
        *,
        ttl_seconds: int,
        cooldown_seconds: int,
    ) -> None:
        self.redis = redis_client
        self.ttl = ttl_seconds
        self.cooldown = cooldown_seconds

    def _token_key(self, token: str) -> str:
        return f"{self.prefix}token:{_digest(token)}"

    def _user_key(self, user_id: bytes | str) -> str:
        return f"{self.prefix}user:{user_id_to_string(user_id)}"

    def _cooldown_key(self, user_id: bytes | str) -> str:
        return f"{self.prefix}cooldown:{user_id_to_string(user_id)}"

    async def claim_send_slot(self, user_id: bytes | str) -> bool:
        """Allow one reset email per cooldown window; False means wait."""
        return bool(
            await self.redis.set(
                self._cooldown_key(user_id), "1", nx=True, ex=self.cooldown
            )
        )

    async def release_send_slot(self, user_id: bytes | str) -> None:
        await self.redis.delete(self._cooldown_key(user_id))

    async def create_token(self, user_id: bytes | str) -> str:
        """Issue a new link token. Any earlier link for the user stops working."""
        await self._revoke_current(user_id)
        token = secrets.token_urlsafe(32)
        await self.redis.set(
            self._token_key(token), user_id_to_string(user_id), ex=self.ttl
        )
        await self.redis.set(self._user_key(user_id), _digest(token), ex=self.ttl)
        return token

    async def consume_token(self, token: str) -> str | None:
        """Return the user id for a valid token and spend it, else None."""
        # GETDEL is atomic, so two requests with the same link cannot both win.
        user_id = await self.redis.getdel(self._token_key(token))
        if user_id:
            await self.redis.delete(self._user_key(user_id))
        return user_id

    async def revoke(self, user_id: bytes | str) -> None:
        await self._revoke_current(user_id)
        await self.redis.delete(self._user_key(user_id))

    async def _revoke_current(self, user_id: bytes | str) -> None:
        digest = await self.redis.get(self._user_key(user_id))
        if digest:
            await self.redis.delete(f"{self.prefix}token:{digest}")
