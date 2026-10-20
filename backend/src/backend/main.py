# backend/main.py
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.router import api_v1_router
from backend.core.config import settings
from backend.core.exceptions import AppException
from backend.db.session import engine, get_db

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 1. Initialize Redis connection pool
    app.state.redis = aioredis.from_url(
        str(settings.REDIS_URL),
        decode_responses=True,
        max_connections=settings.REDIS_POOL_SIZE,
    )
    try:
        await app.state.redis.ping()
    except (aioredis.ConnectionError, aioredis.TimeoutError) as err:
        raise RuntimeError(
            f"Failed to connect to Redis at {settings.REDIS_URL}"
        ) from err

    yield

    # 2. Teardown: close Redis client and dispose SQLAlchemy pool
    await app.state.redis.aclose()
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

# Mandatory for HTTP cookies to be sent across browser origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-CSRF-Token"],
)


# Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.__class__.__name__, "detail": exc.message},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "DatabaseConflict",
            "detail": "A data integrity conflict occurred.",
        },
    )


@app.exception_handler(DBAPIError)
async def dbapi_error_handler(_: Request, exc: DBAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "DatabaseError",
            "detail": "An internal database operation failed.",
        },
    )


# Routers
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


# Health Check with detailed error capture
@app.get("/health", tags=["Monitoring"], status_code=status.HTTP_200_OK)
async def unified_health_check(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    redis_client = request.app.state.redis
    db_error: str | None = None
    redis_error: str | None = None

    async def check_db() -> bool:
        nonlocal db_error
        try:
            result = await db.execute(text("SELECT 1"))
            return bool(result.scalar())
        except Exception as exc:
            db_error = f"{type(exc).__name__}: {exc}"
            logger.error("Health check DB failure: %s", db_error)
            return False

    async def check_redis() -> bool:
        nonlocal redis_error
        try:
            return bool(await redis_client.ping())
        except Exception as exc:
            redis_error = f"{type(exc).__name__}: {exc}"
            logger.error("Health check Redis failure: %s", redis_error)
            return False

    db_ok, redis_ok = await asyncio.gather(check_db(), check_redis())
    healthy = db_ok and redis_ok

    payload = {
        "status": "healthy" if healthy else "degraded",
        "services": {
            "database": {
                "status": "up" if db_ok else "down",
                **({"error": db_error} if db_error else {}),
            },
            "redis": {
                "status": "up" if redis_ok else "down",
                **({"error": redis_error} if redis_error else {}),
            },
        },
    }

    return JSONResponse(
        status_code=status.HTTP_200_OK
        if healthy
        else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload,
    )
