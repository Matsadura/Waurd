import json
import uuid
from datetime import datetime

from redis.asyncio import Redis


# Lua Script 1: Atomic Queue Join (prevents duplicate queueing & partial writes)
LUA_JOIN_QUEUE = """
local user_key = KEYS[1]
local queue_key = KEYS[2]
local user_id = ARGV[1]
local ticket_json = ARGV[2]
local ttl = tonumber(ARGV[3])

if redis.call("EXISTS", user_key) == 1 then
    return redis.call("GET", user_key)
end

redis.call("SET", user_key, ticket_json, "EX", ttl)
redis.call("RPUSH", queue_key, user_id)
return ticket_json
"""


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

        ticket_data = {
            "ticket_id": str(uuid.uuid4()),
            "user_id": user_id_str,
            "time_control_seconds": time_control,
            "status": "QUEUED",
            "queued_at": datetime.utcnow().isoformat(),
            "matched_match_id": None,
        }
        res_raw = await self.redis.eval(
            LUA_JOIN_QUEUE,
            2,
            user_key,
            queue_key,
            user_id_str,
            json.dumps(ticket_data),
            600,
        )
        return json.loads(res_raw)

    async def get_user_ticket(self, user_id_str: str) -> dict | None:
        """Fetches active queue ticket for a given user."""
        user_key = self._user_key(user_id_str)
        raw_data = await self.redis.get(user_key)
        if raw_data:
            return json.loads(raw_data)
        return None
