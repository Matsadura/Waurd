# backend/main.py
import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
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
        content={"detail": exc.message},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    error = exc.errors()[0]
    error_type = error.get("type", "")
    context = error.get("ctx", {})
    location = error.get("loc", ())
    field = str(location[-1]) if location else "value"
    field_names = {
        "username": "Username",
        "email": "Email",
        "password": "Password",
        "avatar_url": "Avatar URL",
        "target_user_id": "User ID",
        "user_id": "User ID",
        "request_id": "Request ID",
        "code": "Code",
        "new_password": "Password",
        "token": "Reset token",
    }
    field_name = field_names.get(field, "Value")

    if field == "email" or error_type == "email_parsing":
        detail = "Email must be a valid email address."
    elif error_type == "string_too_short":
        detail = (
            f"{field_name} must be at least {context.get('min_length')} characters."
        )
    elif error_type == "string_too_long":
        detail = f"{field_name} must be at most {context.get('max_length')} characters."
    elif error_type == "missing":
        detail = f"{field_name} is required."
    elif error_type in {"uuid_parsing", "uuid_type"}:
        detail = f"{field_name} is invalid."
    elif error_type == "value_error":
        detail = "Provide a target user ID or username."
    else:
        detail = f"{field_name} is invalid."

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, exc: IntegrityError) -> JSONResponse:
    conflict = str(exc.orig).lower() if exc.orig else str(exc).lower()
    detail = (
        "Username or email already exists."
        if "username" in conflict or "email" in conflict
        else "Data conflict."
    )
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": detail},
    )


@app.exception_handler(DBAPIError)
async def dbapi_error_handler(_: Request, exc: DBAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal database operation failed."},
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
    db_failed = False
    redis_failed = False

    async def check_db() -> bool:
        nonlocal db_failed
        try:
            result = await db.execute(text("SELECT 1"))
            return bool(result.scalar())
        except Exception:
            db_failed = True
            logger.exception("Health check DB failure")
            return False

    async def check_redis() -> bool:
        nonlocal redis_failed
        try:
            return bool(await redis_client.ping())
        except Exception:
            redis_failed = True
            logger.exception("Health check Redis failure")
            return False

    db_ok, redis_ok = await asyncio.gather(check_db(), check_redis())
    healthy = db_ok and redis_ok

    payload = {
        "status": "healthy" if healthy else "degraded",
        "services": {
            "database": {
                "status": "up" if db_ok else "down",
                **({"error": "Database unavailable"} if db_failed else {}),
            },
            "redis": {
                "status": "up" if redis_ok else "down",
                **({"error": "Redis unavailable"} if redis_failed else {}),
            },
        },
    }

    return JSONResponse(
        status_code=status.HTTP_200_OK
        if healthy
        else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload,
    )
