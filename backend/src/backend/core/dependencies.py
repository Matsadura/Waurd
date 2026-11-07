import redis.asyncio as aioredis
from fastapi import Depends, Request

from backend.core.matchmaking_store import MatchmakingQueueStore
from backend.core.session_store import RedisSessionStore


def get_redis_client(request: Request) -> aioredis.Redis:
    return request.app.state.redis


def get_session_store(
    redis: aioredis.Redis = Depends(get_redis_client),
) -> RedisSessionStore:
    return RedisSessionStore(redis_client=redis)


def get_matchmaking_queue(
    redis: aioredis.Redis = Depends(get_redis_client),
) -> MatchmakingQueueStore:
    """Injects MatchmakingQueueStore using the shared Redis connection pool."""
    return MatchmakingQueueStore(redis_client=redis)
