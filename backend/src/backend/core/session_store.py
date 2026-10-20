import json
import secrets
from typing import Any

import redis.asyncio as aioredis


class RedisSessionStore:
    def __init__(
        self, redis_client: aioredis.Redis, ttl_seconds: int = 86400 * 7
    ) -> None:
        self.redis = redis_client
        self.ttl = ttl_seconds
        self.prefix = "session:"

    def _key(self, session_id: str) -> str:
        return f"{self.prefix}{session_id}"

    async def create_session(
        self, user_id: str, metadata: dict[str, Any] | None = None
    ) -> str:
        """Generate a cryptographically secure 256-bit token and persist session state."""
        session_id = secrets.token_urlsafe(32)
        payload = {
            "user_id": user_id,
            "metadata": metadata or {},
        }
        await self.redis.set(
            self._key(session_id),
            json.dumps(payload),
            ex=self.ttl,
        )
        return session_id

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Fetch session and renew TTL (sliding window expiration)."""
        data = await self.redis.get(self._key(session_id))
        if not data:
            return None

        # Extend lease on active access
        await self.redis.expire(self._key(session_id), self.ttl)
        return json.loads(data)

    async def delete_session(self, session_id: str) -> None:
        """Revoke a single session."""
        await self.redis.delete(self._key(session_id))

    async def delete_all_user_sessions(self, user_id: str) -> None:
        """Revoke all sessions for a specific user (e.g., password reset)."""
        pattern = f"{self.prefix}*"
        async for key in self.redis.scan_iter(match=pattern):
            val = await self.redis.get(key)
            if val and json.loads(val).get("user_id") == user_id:
                await self.redis.delete(key)
