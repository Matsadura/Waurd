import json
import uuid
from datetime import datetime, timezone

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

# Lua Script 2: Atomic Cancellation
LUA_CANCEL_QUEUE = """
local user_key = KEYS[1]
local queue_key = KEYS[2]
local user_id = ARGV[1]

local ticket = redis.call("GET", user_key)
if not ticket then
    return 0
end

redis.call("DEL", user_key)
redis.call("LREM", queue_key, 0, user_id)
return 1
"""

# Lua Script 3: Atomic Candidate Claiming
LUA_CLAIM_OPPONENT = """
local candidate_user_key = KEYS[1]
local match_id = ARGV[1]

local ticket_raw = redis.call("GET", candidate_user_key)
if not ticket_raw then
    return nil
end

local ticket = cjson.decode(ticket_raw)
if ticket["status"] ~= "QUEUED" then
    return nil
end

ticket["status"] = "MATCHED"
ticket["matched_match_id"] = match_id
local updated_raw = cjson.encode(ticket)

redis.call("SET", candidate_user_key, updated_raw, "EX", 300)
return updated_raw
"""


class MatchmakingQueueStore:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def _user_key(self, user_id_str: str) -> str:
        return f"matchmaking:user:{user_id_str}"

    def _queue_key(self, time_control: int) -> str:
        return f"matchmaking:queue:{time_control}"

    async def add_to_queue(
        self, user_id_str: str, time_control: int, user_elo: int
    ) -> dict:
        """Adds a user with their Elo rating to the matchmaking pool in Redis."""
        user_key = self._user_key(user_id_str)
        queue_key = self._queue_key(time_control)

        ticket_data = {
            "ticket_id": str(uuid.uuid4()),
            "user_id": user_id_str,
            "time_control_seconds": time_control,
            "elo": user_elo,
            "status": "QUEUED",
            "queued_at": datetime.now(timezone.utc).isoformat(),
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

    async def cancel_queue(self, user_id_str: str, time_control: int) -> bool:
        """Atomically removes a user from the queue list and deletes their ticket key."""
        user_key = self._user_key(user_id_str)
        queue_key = self._queue_key(time_control)

        res = await self.redis.eval(
            LUA_CANCEL_QUEUE,
            2,
            user_key,
            queue_key,
            user_id_str,
        )
        return bool(res)

    async def claim_candidate(
        self, candidate_id_str: str, match_id_str: str
    ) -> dict | None:
        """Atomically transitions candidate ticket status to MATCHED for background matchmaker."""
        candidate_key = self._user_key(candidate_id_str)
        res_raw = await self.redis.eval(
            LUA_CLAIM_OPPONENT,
            1,
            candidate_key,
            match_id_str,
        )
        if res_raw:
            return json.loads(res_raw)
        return None

    async def get_user_ticket(self, user_id_str: str) -> dict | None:
        """Fetches active queue ticket for a given user."""
        user_key = self._user_key(user_id_str)
        raw_data = await self.redis.get(user_key)
        if raw_data:
            return json.loads(raw_data)
        return None
