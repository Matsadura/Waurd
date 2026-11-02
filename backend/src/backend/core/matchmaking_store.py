import json
import uuid
from datetime import datetime

from redis.asyncio import Redis


class MatchmakingQueueStore:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def _user_key(self, user_id_str: str) -> str:
        return f"matchmaking:user:{user_id_str}"

    def _queue_key(self, time_control: int) -> str:
        return f"matchmaking:queue:{time_control}"

    async def add_to_queue(self, user_id_str: str, time_control: int) -> dict:
        """Adds a user to the matchmaking pool in Redis if not already queued."""
        user_key = self._user_key(user_id_str)
        queue_key = self._queue_key(time_control)

        # Check if already queued
        existing_ticket = await self.redis.get(user_key)
        if existing_ticket:
            return json.loads(existing_ticket)

        ticket_id = str(uuid.uuid4())
        queued_at = datetime.utcnow().isoformat()

        ticket_data = {
            "ticket_id": ticket_id,
            "user_id": user_id_str,
            "time_control_seconds": time_control,
            "status": "QUEUED",
            "queued_at": queued_at,
            "matched_match_id": None,
        }

        # Store user ticket state (expires in 10 minutes max if abandoned)
        await self.redis.set(user_key, json.dumps(ticket_data), ex=600)
        # Push user ID to queue list for this time control
        await self.redis.rpush(queue_key, user_id_str)

        return ticket_data

    async def get_user_ticket(self, user_id_str: str) -> dict | None:
        """Fetches active queue ticket for a given user."""
        user_key = self._user_key(user_id_str)
        raw_data = await self.redis.get(user_key)
        if raw_data:
            return json.loads(raw_data)
        return None
