from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.exceptions import AppException
from backend.db.session import get_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup actions
    yield
    # Shutdown actions


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.__class__.__name__, "detail": exc.message},
    )

@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, exc: IntegrityError) -> JSONResponse:
    # Catches unexpected unique constraint or foreign key violations from MySQL
    return JSONResponse(
        status_code=409,
        content={"error": "DatabaseConflict", "detail": "A data integrity conflict occurred."},
    )

@app.exception_handler(DBAPIError)
async def dbapi_error_handler(_: Request, exc: DBAPIError) -> JSONResponse:
    # Shield raw database errors from leaking to users
    return JSONResponse(
        status_code=500,
        content={"error": "DatabaseError", "detail": "An internal database operation failed."},
    )

@app.get("/health", tags=["Monitoring"])
async def health_check(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT 1"))
    return {"status": "ok", "db_connected": bool(result.scalar())}
