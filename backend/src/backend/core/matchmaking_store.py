import json
import uuid
from datetime import datetime, timezone

from redis.asyncio import Redis

from backend.core.exceptions import BadRequestException

# Script 1: Atomic Queue Join
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

# Script 2: Atomic Queue Cancellation
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

# Script 3: Atomic Opponent Candidate Claiming
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
        # Pre-compile scripts into SHA1 hashes for EVALSHA execution
        self._join_script = self.redis.register_script(LUA_JOIN_QUEUE)
        self._cancel_script = self.redis.register_script(LUA_CANCEL_QUEUE)
        self._claim_script = self.redis.register_script(LUA_CLAIM_OPPONENT)

    def _user_key(self, user_id_str: str, time_control: int) -> str:
        # Hash tag {time_control} guarantees user_key and queue_key land on the same Redis cluster slot
        return f"matchmaking:{{{time_control}}}:user:{user_id_str}"

    def _queue_key(self, time_control: int) -> str:
        return f"matchmaking:{{{time_control}}}:queue"

    async def add_to_queue(
        self, user_id_str: str, time_control: int, user_elo: int
    ) -> dict:
        """Adds a user with their Elo rating to the matchmaking pool in Redis."""
        user_key = self._user_key(user_id_str, time_control)
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

        # Execute via EVALSHA registered script
        res_raw = await self._join_script(
            keys=[user_key, queue_key],
            args=[user_id_str, json.dumps(ticket_data), 600],
        )

        if res_raw is None:
            raise BadRequestException("Failed to process matchmaking queue request.")

        if isinstance(res_raw, bytes):
            res_raw = res_raw.decode("utf-8")

        try:
            return json.loads(res_raw)
        except (json.JSONDecodeError, TypeError):
            raise BadRequestException("Invalid data structure returned from queue engine.")

    async def cancel_queue(self, user_id_str: str, time_control: int) -> bool:
        """Atomically removes a user from the queue list and deletes their ticket key."""
        user_key = self._user_key(user_id_str, time_control)
        queue_key = self._queue_key(time_control)

        res = await self._cancel_script(
            keys=[user_key, queue_key],
            args=[user_id_str],
        )
        return bool(res)

    async def claim_candidate(
        self, candidate_id_str: str, time_control: int, match_id_str: str
    ) -> dict | None:
        """Atomically transitions candidate ticket status to MATCHED for background matchmaker."""
        candidate_key = self._user_key(candidate_id_str, time_control)
        res_raw = await self._claim_script(
            keys=[candidate_key],
            args=[match_id_str],
        )

        if not res_raw:
            return None

        if isinstance(res_raw, bytes):
            res_raw = res_raw.decode("utf-8")

        try:
            return json.loads(res_raw)
        except (json.JSONDecodeError, TypeError):
            return None

    async def get_user_ticket(
        self, user_id_str: str, time_control: int
    ) -> dict | None:
        """Fetches active queue ticket for a given user."""
        user_key = self._user_key(user_id_str, time_control)
        raw_data = await self.redis.get(user_key)

        if not raw_data:
            return None

        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode("utf-8")

        try:
            return json.loads(raw_data)
        except (json.JSONDecodeError, TypeError):
            return None