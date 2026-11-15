import json
import uuid
from datetime import UTC, datetime

from redis.asyncio import Redis

from backend.core.exceptions import BadRequestException

# Script 1: Atomic Queue Join with Automatic Time-Control Switching
LUA_JOIN_QUEUE = """
local user_key = KEYS[1]
local new_queue_key = KEYS[2]
local user_id = ARGV[1]
local ticket_json = ARGV[2]
local ttl = tonumber(ARGV[3])
local new_tc = ARGV[4]
local expected_old_tc = ARGV[5]

local existing_raw = redis.call("GET", user_key)
if existing_raw then
    local existing = cjson.decode(existing_raw)

    if existing["status"] == "MATCHED" or existing["status"] == "CLAIMING" then
        return "ERR_ALREADY_MATCHED"
    end

    if tostring(existing["time_control_seconds"]) == new_tc then
        return existing_raw
    end

    if expected_old_tc == "" or tostring(existing["time_control_seconds"]) ~= expected_old_tc then
        return "ERR_RETRY"
    end

    -- Atomically remove user from their previous time-control queue
    local old_queue_key = KEYS[3]
    redis.call("LREM", old_queue_key, 0, user_id)
end

redis.call("SET", user_key, ticket_json, "EX", ttl)
redis.call("RPUSH", new_queue_key, user_id)
return ticket_json
"""

# Script 2: Atomic Queue Cancellation
LUA_CANCEL_QUEUE = """
local user_key = KEYS[1]
local queue_key = KEYS[2]
local user_id = ARGV[1]
local expected_tc = ARGV[2]

local ticket_raw = redis.call("GET", user_key)
if not ticket_raw then
    return 0
end

local ticket = cjson.decode(ticket_raw)
if ticket["status"] ~= "QUEUED" then
    return 0
end

if expected_tc ~= "" and tostring(ticket["time_control_seconds"]) ~= expected_tc then
    return 0
end

redis.call("DEL", user_key)
redis.call("LREM", queue_key, 0, user_id)
return 1
"""

# Script 3: Atomic Two-Player Claim Lock (10s TTL while MySQL commits)
LUA_CLAIM_PAIR = """
local p1_key = KEYS[1]
local p2_key = KEYS[2]
local expected_tc = ARGV[1]

local raw1 = redis.call("GET", p1_key)
local raw2 = redis.call("GET", p2_key)
if not raw1 or not raw2 then
    return nil
end

local t1 = cjson.decode(raw1)
local t2 = cjson.decode(raw2)

if t1["status"] ~= "QUEUED" or tostring(t1["time_control_seconds"]) ~= expected_tc then
    return nil
end
if t2["status"] ~= "QUEUED" or tostring(t2["time_control_seconds"]) ~= expected_tc then
    return nil
end

t1["status"] = "CLAIMING"
t2["status"] = "CLAIMING"

redis.call("SET", p1_key, cjson.encode(t1), "EX", 10)
redis.call("SET", p2_key, cjson.encode(t2), "EX", 10)
return 1
"""


class MatchmakingQueueStore:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self._join_script = self.redis.register_script(LUA_JOIN_QUEUE)
        self._cancel_script = self.redis.register_script(LUA_CANCEL_QUEUE)
        self._claim_pair_script = self.redis.register_script(LUA_CLAIM_PAIR)

    def _user_key(self, user_id_str: str) -> str:
        return f"matchmaking:user:{user_id_str}"

    def _queue_key(self, time_control: int) -> str:
        return f"matchmaking:queue:{time_control}"

    async def add_to_queue(
        self, user_id_str: str, time_control: int, user_elo: int
    ) -> dict:
        """
        Adds a user to the requested time-control queue.
        If already queued under a different time control, atomically removes them
        from the old queue before joining the new one.
        """
        user_key = self._user_key(user_id_str)
        new_queue_key = self._queue_key(time_control)

        ticket_data = {
            "ticket_id": str(uuid.uuid4()),
            "user_id": user_id_str,
            "time_control_seconds": time_control,
            "elo": user_elo,
            "status": "QUEUED",
            "queued_at": datetime.now(UTC).isoformat(),
            "matched_match_id": None,
        }
        ticket_json = json.dumps(ticket_data)

        for _ in range(2):
            existing = await self.get_user_ticket(user_id_str)
            keys = [user_key, new_queue_key]
            expected_old_tc = ""

            if existing:
                if existing.get("status") in ("MATCHED", "CLAIMING"):
                    raise BadRequestException(
                        "You have already been matched into a game."
                    )

                old_tc = existing.get("time_control_seconds")
                if old_tc == time_control:
                    return existing

                if old_tc is not None:
                    keys.append(self._queue_key(int(old_tc)))
                    expected_old_tc = str(old_tc)

            res_raw = await self._join_script(
                keys=keys,
                args=[
                    user_id_str,
                    ticket_json,
                    600,
                    str(time_control),
                    expected_old_tc,
                ],
            )

            if isinstance(res_raw, bytes):
                res_raw = res_raw.decode("utf-8")

            if res_raw == "ERR_RETRY":
                continue
            if res_raw == "ERR_ALREADY_MATCHED":
                raise BadRequestException("You have already been matched into a game.")
            if res_raw is None:
                raise BadRequestException(
                    "Failed to process matchmaking queue request."
                )

            try:
                return json.loads(res_raw)
            except (json.JSONDecodeError, TypeError):
                raise BadRequestException("Invalid data returned from queue engine.")

        raise BadRequestException("Concurrent queue update detected. Please try again.")

    async def cancel_queue(
        self, user_id_str: str, time_control: int | None = None
    ) -> bool:
        """Atomically removes a user from their active queue and deletes their ticket."""
        existing = await self.get_user_ticket(user_id_str)
        if not existing:
            return False

        active_tc = existing.get("time_control_seconds")
        if active_tc is None:
            return False

        if time_control is not None and int(active_tc) != time_control:
            return False

        res = await self._cancel_script(
            keys=[self._user_key(user_id_str), self._queue_key(int(active_tc))],
            args=[user_id_str, str(active_tc)],
        )
        return bool(res)

    async def claim_pair(
        self, player1_id_str: str, player2_id_str: str, time_control: int
    ) -> bool:
        """Atomically locks two QUEUED players for 10s while the DB match is committed."""
        res = await self._claim_pair_script(
            keys=[self._user_key(player1_id_str), self._user_key(player2_id_str)],
            args=[str(time_control)],
        )
        return bool(res)

    async def finalize_matched_pair(
        self,
        player1_id_str: str,
        player2_id_str: str,
        time_control: int,
        match_id: str | None = None,
    ) -> None:
        """Removes players from queue list and updates their ticket status to MATCHED in Redis for 60s."""
        queue_key = self._queue_key(time_control)
        pipe = self.redis.pipeline()
        pipe.lrem(queue_key, 0, player1_id_str)
        pipe.lrem(queue_key, 0, player2_id_str)

        for uid in (player1_id_str, player2_id_str):
            user_key = self._user_key(uid)
            raw = await self.redis.get(user_key)
            if raw:
                try:
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8")
                    data = json.loads(raw)
                    data["status"] = "MATCHED"
                    if match_id:
                        data["matched_match_id"] = match_id
                    pipe.set(user_key, json.dumps(data), ex=60)
                except (json.JSONDecodeError, TypeError, KeyError):
                    pipe.delete(user_key)
            else:
                pipe.delete(user_key)

        await pipe.execute()

    async def get_user_ticket(self, user_id_str: str) -> dict | None:
        """Fetches the single active queue ticket for a user."""
        raw_data = await self.redis.get(self._user_key(user_id_str))
        if not raw_data:
            return None

        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode("utf-8")

        try:
            return json.loads(raw_data)
        except (json.JSONDecodeError, TypeError):
            return None
